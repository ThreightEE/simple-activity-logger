from django.db import models

from realtime_config.realtime_config import get_config


class ActivityType:
    """
    Constants for types of physical activities, as custom enum implementation.
    """

    # Enum values as class attributes
    RUN = 'run'
    WALK = 'walk'
    CYCLE = 'cycle'
    SWIM = 'swim'
    YOGA = 'yoga'
    # for easy reference and validation
    _ALL_VALUES = (RUN, WALK, CYCLE, SWIM, YOGA)

    _LABELS = {
        RUN: 'Running',
        WALK: 'Walking',
        CYCLE: 'Cycling',
        SWIM: 'Swimming',
        YOGA: 'Yoga'
    }

    # Mapping between activity types and config keys in constance
    _MET_CONFIG_KEYS = {
        RUN: 'MET_RUN',
        WALK: 'MET_WALK',
        CYCLE: 'MET_CYCLE',
        SWIM: 'MET_SWIM',
        YOGA: 'MET_YOGA'
    }

    # for calorie burn calculation for particular activity
    _DEFAULT_MET_VALUES = {
        RUN: 9.0,
        WALK: 3.5,
        CYCLE: 8.0,
        SWIM: 6.5,
        YOGA: 4.0
    }
    
    @classmethod
    def is_valid(cls, value: str) -> bool:
        """Check if value is an activity type"""
        return value in cls._ALL_VALUES

    @classmethod
    def validate(cls, value: str) -> str:
        """Return the value if valid, otherwise error"""
        if not cls.is_valid(value):
            valid_values = ", ".join(cls._ALL_VALUES)
            raise ValueError(f"Invalid activity type: {value}. Must be one of: {valid_values}")
        return value
    
    @classmethod
    def choices(cls) -> list[tuple[str, str]]:
        """Return list of tuples for Django model choices"""
        return [(value, cls._LABELS[value]) for value in cls._ALL_VALUES]
    
    @classmethod
    def get_label(cls, value: str) -> str:
        """Return readable label for activity value"""
        value = cls.validate(value)
        return cls._LABELS[value]
    
    @classmethod
    def get_met(cls, value: str) -> float:
        """Return MET value for activity value"""
        value = cls.validate(value)
        # Get constance config key for this activity type
        config_key = cls._MET_CONFIG_KEYS.get(value)

        if not config_key:
            return cls._DEFAULT_MET_VALUES.get(value, 1.0)
        
        # Get MET value from realtime config with fallback to default
        met_value = get_config(config_key, cls._DEFAULT_MET_VALUES.get(value, 1.0))
        return float(met_value)
    
# Choices for status field in Activity model
class ProcessingStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    PROCESSING = 'PROCESSING', 'Processing'
    COMPLETED = 'COMPLETED', 'Completed'
    FAILED = 'FAILED', 'Failed'
