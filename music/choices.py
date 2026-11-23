
from django.db import models


class SyncRatio(models.TextChoices):
    """
    Relationship between running steps and musical beats.

    Ratio represents musical beats per running step.
    """

    HALF_TIME = "0.5", "One beat per two steps"
    ONE_TO_ONE = "1.0", "One beat per step"
    DOUBLE_TIME = "2.0", "Two beats per step"
