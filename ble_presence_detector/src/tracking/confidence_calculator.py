"""Confidence calculation using exponential decay."""

import math
from datetime import datetime


class ConfidenceCalculator:
    """Calculates confidence using exponential decay.

    Confidence starts at 1.0 when a device is detected and decays exponentially
    over time. This models the increasing uncertainty about device presence
    as time passes since last detection.

    The decay follows: confidence = initial * e^(-λt)

    Where:
    - λ (lambda) is the decay rate
    - t is time since last detection in seconds

    The half-life is the time for confidence to drop to 0.5:
    half_life = ln(2) / λ
    """

    def __init__(self, decay_rate: float, half_life_seconds: float = 30.0):
        """Initialize confidence calculator.

        Args:
            decay_rate: Decay rate parameter (higher = faster decay)
            half_life_seconds: Time for confidence to reach 0.5

        Note:
            If both are provided, decay_rate takes precedence.
            Typical values:
            - decay_rate=0.1 → half_life ≈ 6.9 seconds
            - decay_rate=0.05 → half_life ≈ 13.9 seconds
            - half_life=30s → decay_rate ≈ 0.023
        """
        self._decay_rate = decay_rate
        self._half_life = half_life_seconds

        calculated_half_life = math.log(2) / decay_rate if decay_rate > 0 else float('inf')

        if abs(calculated_half_life - half_life_seconds) > 1.0:
            import logging
            logger = logging.getLogger(__name__)
            logger.debug(
                f"Decay rate {decay_rate} gives half-life of {calculated_half_life:.1f}s "
                f"(configured: {half_life_seconds}s)"
            )

    def calculate(self, last_seen: datetime, initial_confidence: float = 1.0,
                 current_time: Optional[datetime] = None) -> float:
        """Calculate current confidence based on time since last detection.

        Args:
            last_seen: When device was last detected
            initial_confidence: Starting confidence (typically 1.0)
            current_time: Current time (defaults to now)

        Returns:
            Current confidence level (0.0 - 1.0)
        """
        if current_time is None:
            current_time = datetime.now()

        time_elapsed = (current_time - last_seen).total_seconds()

        if time_elapsed < 0:
            time_elapsed = 0

        confidence = initial_confidence * math.exp(-self._decay_rate * time_elapsed)

        return max(0.0, min(1.0, confidence))

    def is_present(self, confidence: float, threshold: float = 0.5) -> bool:
        """Determine if device is considered present based on confidence.

        Args:
            confidence: Current confidence level
            threshold: Minimum confidence for presence

        Returns:
            True if confidence >= threshold
        """
        return confidence >= threshold

    def time_to_threshold(self, threshold: float = 0.5,
                         initial_confidence: float = 1.0) -> float:
        """Calculate time until confidence drops below threshold.

        Useful for determining how long a device will be considered
        present after last detection.

        Args:
            threshold: Target confidence threshold
            initial_confidence: Starting confidence

        Returns:
            Time in seconds until threshold is reached
        """
        if threshold >= initial_confidence or self._decay_rate == 0:
            return float('inf')

        if threshold <= 0:
            return float('inf')

        return -math.log(threshold / initial_confidence) / self._decay_rate

    @property
    def decay_rate(self) -> float:
        """Get the decay rate."""
        return self._decay_rate

    @property
    def half_life(self) -> float:
        """Get the half-life in seconds."""
        if self._decay_rate == 0:
            return float('inf')
        return math.log(2) / self._decay_rate
