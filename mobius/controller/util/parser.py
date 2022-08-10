import json
from types import SimpleNamespace

import yaml


class Evaluator:
    def __init__(self, all_providers, all_resources):
        self.providers = all_providers
        self.resources = all_resources

    def find_object(self, path: str):
        parts = path.split('.')
        objects = self.providers + self.resources

        if len(parts) > 2:
            raise Exception(f"this {path} is not handled just yet")

        for obj in objects:
            if obj.type == parts[0] and obj.name == parts[1]:
                return obj

        raise Exception(f"object not found at {path}")

    @staticmethod
    def _normalize(objs):  # TODO Remove ... (This is to integrate quickly).
        for obj in objs:
            attrs = {}

            for key, value in obj.attributes.items():
                if isinstance(value, SimpleNamespace):
                    attrs[key] = vars(value)
                else:
                    attrs[key] = value

            obj.attributes = attrs

    def evaluate(self):
        for obj in self.resources:
            attrs = {}

            for key, value in obj.attributes.items():
                attrs[key] = value

                if isinstance(value, str):
                    value = value.strip()

                    if value.startswith('{{') and value.endswith('}}'):
                        path = value[2:-2].strip()
                        attrs[key] = self.find_object(path)

                if isinstance(value, SimpleNamespace):
                    attrs[key] = vars(value)

            obj.attributes = attrs

        self._normalize(self.providers)
        self._normalize(self.resources)
        return self.providers, self.resources


class Parser:
    def __init__(self):
        pass

    @staticmethod
    def _parse_object(obj):
        def extract_label(lst):
            return next(label for label in lst if not label.startswith("__"))

        typ = extract_label(dir(obj))
        value = obj.__getattribute__(typ)[0]
        name = extract_label(dir(value))
        value = value.__getattribute__(name)[0]
        attrs = value.__dict__
        return SimpleNamespace(type=typ, name=name, attributes=attrs)

    @staticmethod
    def parse(file_name):
        def load_object(dct):
            return SimpleNamespace(**dct)

        with open(file_name, 'r') as stream:
            obj = yaml.safe_load(stream)
            obj = json.loads(json.dumps(obj), object_hook=load_object)

        providers = [Parser._parse_object(provider) for provider in obj.provider]
        resources = [Parser._parse_object(resource) for resource in obj.resource]
        evaluator = Evaluator(providers, resources)
        return evaluator.evaluate()
