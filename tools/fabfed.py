import sys

from fabfed.controller.controller import Controller
from fabfed.controller.provider_factory import default_provider_factory
from fabfed.exceptions import ControllerException
from fabfed.util import utils
from fabfed.util import state as sutil
from fabfed.util.config import WorkflowConfig


def manage_workflow(args):
    logger = utils.init_logger()

    var_dict = utils.load_vars(args.var_file) if args.var_file else {}

    if args.validate:
        try:
            WorkflowConfig(dir_path=args.config_dir, var_dict=var_dict)
            logger.info("config looks ok")
        except Exception as e:
            logger.error(f"Validation failed .... {type(e)} {e}")
            logger.error(e, exc_info=True)
            sys.exit(1)

    if args.apply:
        config = WorkflowConfig(dir_path=args.config_dir, var_dict=var_dict)

        try:
            controller = Controller(config=config, logger=logger)
        except Exception as e:
            logger.error(f"Exceptions while initializing controller .... {e}")
            sys.exit(1)

        try:
            controller.init(session=args.session, provider_factory=default_provider_factory)
        except Exception as e:
            logger.error(f"Exceptions while initializing providers  .... {e}")
            sys.exit(1)

        try:
            controller.plan()
        except ControllerException as e:
            logger.error(f"Exceptions while adding resources ... {e}")

        try:
            controller.create()
        except ControllerException as e:
            logger.error(f"Exceptions while creating resources ... {e}")

        states = controller.get_states()
        pending = 0
        nodes = 0
        networks = 0
        services = 0
        failed = 0

        for state in states:
            pending += len(state.pending)
            nodes += len([n for n in state.node_states if n.label not in state.failed])
            networks += len([n for n in state.network_states if n.label not in state.failed])
            services += len([s for s in state.service_states if s.label not in state.failed])
            failed += len(state.failed)

        logger.info(f"nodes={nodes}, networks={networks}, services={services}, pending={pending}, failed={failed}")
        sutil.save_states(states, args.session)
        return

    if args.plan:
        config = WorkflowConfig(dir_path=args.config_dir, var_dict=var_dict)
        controller = Controller(config=config, logger=logger)
        controller.init(session=args.session, provider_factory=default_provider_factory)

        try:
            controller.plan()
        except ControllerException as e:
            logger.error(f"Exceptions while adding resources ... {e}")

        states = controller.get_states()
        sutil.dump_states(states, args.json)
        return

    if args.show:
        states = sutil.load_states(args.session)
        sutil.dump_states(states, args.json)
        return

    if args.summary:
        states = sutil.load_states(args.session)
        temp = []

        for provider_state in states:
            for node_state in provider_state.node_states:
                attributes = dict()
                props = ['mgmt_ip', 'username', 'site', 'state', 'id']

                for prop in props:
                    attributes[prop] = node_state.attributes[prop]
                node_state.attributes = attributes
                temp.append(node_state)

        sutil.dump_states(temp, args.json)
        return

    if args.destroy:
        states = sutil.load_states(args.session)

        try:
            if states:
                config = WorkflowConfig(dir_path=args.config_dir, var_dict=var_dict)
                controller = Controller(config=config, logger=logger)
                controller.init(session=args.session, provider_factory=default_provider_factory)
                controller.delete(provider_states=states)
        except ControllerException as e:
            logger.error(f"Exceptions while deleting resources ...{e}")
            import traceback

            logger.error(traceback.format_exc())

        sutil.save_states(states, args.session)
        return


def manage_sessions(args):
    if args.show:
        utils.dump_sessions(args.json)
        return


def main(argv=None):
    argv = argv or sys.argv[1:]
    parser = utils.build_parser(manage_workflow=manage_workflow, manage_sessions=manage_sessions)
    args = parser.parse_args(argv)

    if len(args.__dict__) == 0:
        parser.print_usage()
        sys.exit(1)

    args.dispatch_func(args)


if __name__ == "__main__":
    main(sys.argv[1:])
