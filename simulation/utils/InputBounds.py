class InputBounds():
    def __init__(self):
        self.bounds = []

    def __len__(self):
        return len(self.bounds)

    def add_bounds(self, number_of_bounds: int, lower_bound: float, upper_bound: float):
        self.bounds += [(lower_bound, upper_bound) for _ in range(number_of_bounds)]
        return self

    def add_bound(self, lower_bound: float, upper_bound: float):
        self.bounds.append((lower_bound, upper_bound))
        return self

    def remove_bound(self, index: int):
        self.bounds.pop(index)
        return self

    def get_bound_dict(self):
        bound_dict = {}
        for index, bound in enumerate(self.bounds):
            bound_dict[f"x{index}"] = (bound[0], bound[1])
        return bound_dict

    def get_bounds(self):
        return self.bounds
