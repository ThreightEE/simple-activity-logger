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

    # for calorie burn calculation for particular activity
    _MET_VALUES = {
        RUN: 9.0,
        WALK: 3.5,
        CYCLE: 8.0,
        SWIM: 6.5,
        YOGA: 4.0
    }
    
    @classmethod
    def is_valid(cls, value):
        """Check if value is an activity type"""
        return value in cls._ALL_VALUES

    @classmethod
    def validate(cls, value):
        """Return the value if valid, otherwise error"""
        if not cls.is_valid(value):
            valid_values = ", ".join(cls._ALL_VALUES)
            raise ValueError(f"Invalid activity type: {value}. Must be one of: {valid_values}")
        return value
    
    @classmethod
    def choices(cls):
        """Return list of tuples for Django model choices"""
        return [(value, cls._LABELS[value]) for value in cls._ALL_VALUES]
    
    @classmethod
    def get_label(cls, value):
        """Return readable label for activity value"""
        value = cls.validate(value)  # Using the common validation method
        return cls._LABELS[value]
    
    @classmethod
    def get_met(cls, value):
        """Return MET value for activity value"""
        value = cls.validate(value)  # Using the common validation method
        return cls._MET_VALUES[value]