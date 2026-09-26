class ProblemItem:
    def __init__(self, message: str, solution: str, objects: list[object],
                 icon: str = "OBJECT_DATA", *, category: str = "General",
                 severity: str = "WARNING"):
        self.message = message
        self.solution = solution
        self.icon = icon
        self.category = category
        self.severity = severity
        self.objects = tuple(objects)
        names = []
        for source in self.objects:
            name = getattr(source, "name", "") or type(source).__name__
            if not names or names[-1] != name:
                names.append(name)
        self.name = " / ".join(names) or "Blend file"
        self.path = " > ".join(repr(source) for source in self.objects)

    @property
    def source(self) -> object | None:
        return self.objects[-1] if self.objects else None
