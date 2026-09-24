class ProblemItem():
    message: str
    path: str
    solution: str
    icon: str
    name: str
    def __init__(self, message: str, solution: str, objects: list[any], icon: str = "OBJECT_DATA"):
        for i in objects:
            self.path = repr(i)
            if hasattr(i, "name"):
                self.name = i.name
        self.message = message
        self.solution = solution
        self.icon = icon
