from mobius.controller.controller import Controller

if __name__ == "__main__":
    controller = Controller(config_file_location="new_config.yml")

    controller.create()
    resources = controller.get_resources()

    for r in resources:
        print(r)
        print(r.list_nodes())
