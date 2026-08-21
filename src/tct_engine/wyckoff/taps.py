from dataclasses import dataclass, replace
from enum import Enum, auto

from tct_engine.domain.market_data import Candle
from tct_engine.wyckoff.range import (
    DeviationStatus,
    DeviationTracker,
    RangeSide,
    WyckoffRange,
)


class TapModelStatus(Enum):
    WATCHING_TAP_2 = auto()
    WATCHING_TAP_3 = auto()
    TAP_3_ACTIVE = auto()
    READY_FOR_ENTRY = auto()
    INVALIDATED = auto()
    REPULL_REQUIRED = auto()


@dataclass(frozen=True, slots=True)
class Tap:
    number: int
    price: float
    candle: Candle


@dataclass(frozen=True, slots=True)
class TapSpacing:
    tap_1_to_2_bars: int
    tap_2_to_3_bars: int | None = None

    @property
    def ratio(self) -> float | None:
        if self.tap_2_to_3_bars is None:
            return None

        if self.tap_1_to_2_bars == 0:
            return None

        return self.tap_2_to_3_bars / self.tap_1_to_2_bars


@dataclass(frozen=True, slots=True)
class TapState:
    wyckoff_range: WyckoffRange
    tap_1: Tap
    tap_2: Tap | None
    tap_3: Tap | None
    spacing: TapSpacing | None
    status: TapModelStatus
    bos_search_armed: bool = False
    invalidation_reason: str | None = None


class TapStateMachine:
    """Track the simple consecutive-deviation Wyckoff tap sequence."""

    def __init__(
        self,
        *,
        wyckoff_range: WyckoffRange,
        tap_1_candle: Candle,
        lower_limit: float,
        upper_limit: float,
    ) -> None:
        if wyckoff_range.tap_count != 1:
            raise ValueError("Tap state machine must begin from Tap 1.")

        if not tap_1_candle.is_closed:
            raise ValueError("Tap 1 candle must be closed.")

        self._lower_limit = lower_limit
        self._upper_limit = upper_limit

        tap_1_price = (
            tap_1_candle.low if wyckoff_range.side is RangeSide.ACCUMULATION else tap_1_candle.high
        )

        self._state = TapState(
            wyckoff_range=wyckoff_range,
            tap_1=Tap(
                number=1,
                price=tap_1_price,
                candle=tap_1_candle,
            ),
            tap_2=None,
            tap_3=None,
            spacing=None,
            status=TapModelStatus.WATCHING_TAP_2,
        )

        self._deviation_tracker: DeviationTracker | None = None

    @property
    def state(self) -> TapState:
        return self._state

    def process_bar(self, candle: Candle) -> TapState:
        if not candle.is_closed:
            raise ValueError("Tap tracking requires a closed candle.")

        if self._state.status in {
            TapModelStatus.INVALIDATED,
            TapModelStatus.REPULL_REQUIRED,
            TapModelStatus.READY_FOR_ENTRY,
        }:
            return self._state

        if self._state.status is TapModelStatus.WATCHING_TAP_3 and self._opposite_boundary_reached(
            candle
        ):
            self._state = replace(
                self._state,
                status=TapModelStatus.REPULL_REQUIRED,
                invalidation_reason=("Opposite range boundary reached between Tap 2 and Tap 3."),
            )
            return self._state

        if self._deviation_tracker is None:
            if not self._deviation_started(candle):
                self._check_tap_3_spacing_timeout(candle)
                return self._state

            self._deviation_tracker = DeviationTracker(
                wyckoff_range=self._state.wyckoff_range,
                lower_limit=self._lower_limit,
                upper_limit=self._upper_limit,
            )

            deviation = self._deviation_tracker.process_bar(candle)

            if self._state.status is TapModelStatus.WATCHING_TAP_3:
                if not self._tap_3_spacing_is_valid(candle):
                    self._state = replace(
                        self._state,
                        status=TapModelStatus.REPULL_REQUIRED,
                        invalidation_reason=(
                            "Tap 2 to Tap 3 bar distance exceeded " "Tap 1 to Tap 2 distance."
                        ),
                    )
                    return self._state

                self._state = replace(
                    self._state,
                    status=TapModelStatus.TAP_3_ACTIVE,
                    bos_search_armed=True,
                )

            if deviation is not None:
                self._handle_deviation_state(candle)

            return self._state

        deviation = self._deviation_tracker.process_bar(candle)

        if deviation is not None:
            self._handle_deviation_state(candle)

        return self._state

    def bos_target_is_inside_range(self, price: float) -> bool:
        """Entry BOS structure must exist inside the current range."""
        return self._state.wyckoff_range.low < price < self._state.wyckoff_range.high

    def _handle_deviation_state(self, candle: Candle) -> None:
        assert self._deviation_tracker is not None

        deviation = self._deviation_tracker.deviation

        if deviation is None:
            return

        if deviation.status is DeviationStatus.INVALIDATED:
            self._state = replace(
                self._state,
                status=TapModelStatus.INVALIDATED,
                invalidation_reason="Deviation became invalid.",
            )
            return

        if deviation.status is not DeviationStatus.COMPLETED:
            return

        if self._state.status is TapModelStatus.WATCHING_TAP_2:
            self._complete_tap_2(candle)
            return

        if self._state.status is TapModelStatus.TAP_3_ACTIVE:
            self._complete_tap_3(candle)

    def _complete_tap_2(self, candle: Candle) -> None:
        assert self._deviation_tracker is not None
        assert self._deviation_tracker.deviation is not None

        deviation = self._deviation_tracker.deviation

        tap_2 = Tap(
            number=2,
            price=deviation.extreme,
            candle=candle,
        )

        tap_1_to_2_bars = self._bar_distance(
            self._state.tap_1.candle,
            candle,
        )

        updated_range = self._with_new_active_boundary(deviation.extreme)

        self._state = replace(
            self._state,
            wyckoff_range=updated_range,
            tap_2=tap_2,
            spacing=TapSpacing(
                tap_1_to_2_bars=tap_1_to_2_bars,
            ),
            status=TapModelStatus.WATCHING_TAP_3,
        )

        self._deviation_tracker = None

    def _complete_tap_3(self, candle: Candle) -> None:
        assert self._deviation_tracker is not None
        assert self._deviation_tracker.deviation is not None
        assert self._state.tap_2 is not None
        assert self._state.spacing is not None

        deviation = self._deviation_tracker.deviation

        tap_2_to_3_bars = self._bar_distance(
            self._state.tap_2.candle,
            candle,
        )

        updated_range = self._with_new_active_boundary(deviation.extreme)

        self._state = replace(
            self._state,
            wyckoff_range=updated_range,
            tap_3=Tap(
                number=3,
                price=deviation.extreme,
                candle=candle,
            ),
            spacing=replace(
                self._state.spacing,
                tap_2_to_3_bars=tap_2_to_3_bars,
            ),
            status=TapModelStatus.READY_FOR_ENTRY,
            bos_search_armed=True,
        )

        self._deviation_tracker = None

    def _with_new_active_boundary(
        self,
        extreme: float,
    ) -> WyckoffRange:
        if self._state.wyckoff_range.side is RangeSide.ACCUMULATION:
            return replace(
                self._state.wyckoff_range,
                low=extreme,
                tap_count=self._state.wyckoff_range.tap_count + 1,
            )

        return replace(
            self._state.wyckoff_range,
            high=extreme,
            tap_count=self._state.wyckoff_range.tap_count + 1,
        )

    def _deviation_started(self, candle: Candle) -> bool:
        if self._state.wyckoff_range.side is RangeSide.ACCUMULATION:
            return candle.low < self._state.wyckoff_range.low

        return candle.high > self._state.wyckoff_range.high

    def _opposite_boundary_reached(self, candle: Candle) -> bool:
        if self._state.wyckoff_range.side is RangeSide.ACCUMULATION:
            return candle.high >= self._state.wyckoff_range.high

        return candle.low <= self._state.wyckoff_range.low

    def _tap_3_spacing_is_valid(self, candle: Candle) -> bool:
        assert self._state.tap_2 is not None
        assert self._state.spacing is not None

        tap_2_to_3 = self._bar_distance(
            self._state.tap_2.candle,
            candle,
        )

        return tap_2_to_3 <= self._state.spacing.tap_1_to_2_bars

    def _check_tap_3_spacing_timeout(self, candle: Candle) -> None:
        if self._state.status is not TapModelStatus.WATCHING_TAP_3:
            return

        if self._tap_3_spacing_is_valid(candle):
            return

        self._state = replace(
            self._state,
            status=TapModelStatus.REPULL_REQUIRED,
            invalidation_reason=(
                "Tap 2 to Tap 3 bar distance exceeded " "Tap 1 to Tap 2 distance."
            ),
        )

    def _bar_distance(
        self,
        first: Candle,
        second: Candle,
    ) -> int:
        delta_seconds = (second.open_time - first.open_time).total_seconds()

        return int(delta_seconds // self._state.wyckoff_range.timeframe.seconds)
