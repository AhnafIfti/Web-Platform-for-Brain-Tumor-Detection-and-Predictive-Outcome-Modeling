class AnalysisError(Exception):
    """A safe, actionable error that can be displayed in the research UI."""


class InvalidMRI(AnalysisError):
    pass


class ModelUnavailable(AnalysisError):
    pass
