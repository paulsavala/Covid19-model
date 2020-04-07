

class GenericParam:
    def __init__(self, name, min_value, desc, max_value=None, default_value=None, is_int=False, is_pct=False,
                 group=None, show_label=False):
        self.name = name
        self.min_value = min_value
        self.desc = desc
        self.is_int = is_int
        self.is_pct = is_pct
        self.group = group
        self.show_label = show_label

        if group is None and max_value == min_value:
            self.group = 'constant'

        if max_value is None:
            self.max_value = min_value
        else:
            self.max_value = max_value
        if default_value is None:
            self.default_value = (self.min_value + self.max_value) / 2
        else:
            self.default_value = default_value

        if self.min_value != self.max_value:
            self.is_constant = False
        else:
            self.is_constant = True
