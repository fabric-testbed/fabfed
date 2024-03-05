import sys

from fabfed.controller.controller import Controller
from fabfed.controller.provider_factory import default_provider_factory
from fabfed.exceptions import ControllerException
from fabfed.util import utils
from fabfed.util import state as sutil
from fabfed.util.config import WorkflowConfig


def manage_workflow(args):
    logger = utils.init_logger()
    config_dir = utils.absolute_path(args.config_dir)
    sessions = sutil.load_sessions()
    config_dir_from_meta = sutil.load_meta_data(args.session, 'config_dir') if args.session in sessions else None

    if config_dir_from_meta and config_dir_from_meta != config_dir:
        logger.error(f"attempt to use fabfed session {args.session} from the wrong config dir {config_dir} ...")
        logger.warning(f"ATTN: The CORRECT config dir for session {args.session} is {config_dir_from_meta}!!!!!!!")
        sys.exit(1)

    # we skip -show and -destroy
    if args.apply or args.init or args.plan or args.validate:
        sutil.save_meta_data(dict(config_dir=config_dir), args.session)

    var_dict = utils.load_vars(args.var_file) if args.var_file else {}

    from fabfed.policy.policy_helper import load_policy

    policy = load_policy(policy_file=args.policy_file, load_details=False) if args.policy_file else {}

    if args.validate:
        try:
            WorkflowConfig(dir_path=config_dir, var_dict=var_dict)
            logger.info("config looks ok")
        except Exception as e:
            logger.error(f"Validation failed .... {type(e)} {e}")
            logger.error(e, exc_info=True)
            sys.exit(1)

    if args.apply:
        config = WorkflowConfig(dir_path=config_dir, var_dict=var_dict)

        try:
            controller = Controller(config=config,
                                    logger=logger,
                                    policy=policy,
                                    use_local_policy=not args.use_remote_policy)
        except Exception as e:
            logger.error(f"Exceptions while initializing controller .... {e}")
            logger.error(e, exc_info=True)
            sys.exit(1)

        try:
            controller.init(session=args.session, provider_factory=default_provider_factory)
        except Exception as e:
            logger.error(f"Exceptions while initializing providers  .... {e}")
            logger.error(e, exc_info=True)
            sys.exit(1)

        states = sutil.load_states(args.session)

        try:
            controller.plan(provider_states=states)
        except ControllerException as e:
            logger.error(f"Exceptions while adding resources ... {e}")
        except Exception as e:
            logger.error(f"Exceptioin while planning ... {e}")
        except KeyboardInterrupt as kie:
            logger.error(f"Keyboard Interrupt while adding  resources ... {kie}")
            sys.exit(1)

        try:
            controller.create(provider_states=states)
        except KeyboardInterrupt as kie:
            logger.error(f"Keyboard Interrupt while creating resources ... {kie}")
        except ControllerException as ce:
            logger.error(f"Exceptions while creating resources ... {ce}")

        states = controller.get_states()
        pending = 0
        nodes = 0
        networks = 0
        services = 0
        failed = 0

        for state in states:
            pending += len(state.pending)
            pending += len(state.pending_internal)
            nodes += len([n for n in state.node_states if n.label not in state.failed])
            networks += len([n for n in state.network_states if n.label not in state.failed])
            services += len([s for s in state.service_states if s.label not in state.failed])
            failed += len(state.failed)

        logger.info(f"nodes={nodes}, networks={networks}, services={services}, pending={pending}, failed={failed}")
        sutil.save_states(states, args.session)
        return

    if args.init:
        config = WorkflowConfig(dir_path=config_dir, var_dict=var_dict)
        controller = Controller(config=config,
                                logger=logger,
                                policy=policy,
                                use_local_policy=not args.use_remote_policy)
        controller.init(session=args.session, provider_factory=default_provider_factory)
        sutil.dump_resources(resources=controller.resources, to_json=args.json, summary=args.summary)
        return

    if args.plan:
        config = WorkflowConfig(dir_path=config_dir, var_dict=var_dict)
        controller = Controller(config=config,
                                logger=logger,
                                policy=policy,
                                use_local_policy=not args.use_remote_policy)
        controller.init(session=args.session, provider_factory=default_provider_factory)
        states = sutil.load_states(args.session)

        try:
            controller.plan(provider_states=states)
        except ControllerException as e:
            logger.error(f"Exceptions while adding resources ... {e}")

        states = controller.get_states()
        sutil.dump_states(states, args.json, args.summary)
        return

    if args.show:
        states = sutil.load_states(args.session) if args.session in sessions else []
        sutil.dump_states(states, args.json, args.summary)
        return

    if args.destroy:
        states = sutil.load_states(args.session) if args.session in sessions else []

        try:
            if states:
                config = WorkflowConfig(dir_path=config_dir, var_dict=var_dict)
                controller = Controller(config=config,
                                        logger=logger,
                                        policy=policy,
                                        use_local_policy=True)
                controller.init(session=args.session, provider_factory=default_provider_factory)
                controller.delete(provider_states=states)

            if not states:
                if args.session in sessions:
                    logger.info(f"Destroying session {args.session} ...")

                sutil.destroy_session(args.session)
                return
        except ControllerException as e:
            logger.error(f"Exceptions while deleting resources ...{e}")
            import traceback

            logger.error(traceback.format_exc())
        except KeyboardInterrupt as kie:
            logger.error(f"Keyboard Interrupt while deleting resources ... {kie}")
            sys.exit(1)

        sutil.save_states(states, args.session)
        return


def manage_sessions(args):
    if args.show:
        utils.dump_sessions(args.json)
        return


def display_stitch_info(args):
    logger = utils.init_logger()

    if not args.use_remote_policy or args.policy_file:
        from fabfed.policy.policy_helper import load_policy

        policy = load_policy(policy_file=args.policy_file, load_details=args.policy_file is not None)
        logger.info(f"loaded local stitching policy.")
    else:
        from fabfed.policy.policy_helper import load_remote_policy

        attrs = {'credential_file': args.credential_file, 'profile': args.profile}
        default_provider_factory.init_provider(type='fabric',
                                               label='no_label',
                                               name='no_name',
                                               attributes=attrs,
                                               logger=logger)
        policy = load_remote_policy()
        logger.info(f"loaded remote stitching policy.")

    providers = args.providers.split(",")

    if len(providers) != 2:
        logger.error("please input two providers")
        sys.exit(1)

    for provider in providers:
        if provider not in policy:
            logger.error(f"Did not find provider {provider} in policy file")
            sys.exit(1)

    from fabfed.policy.policy_helper import find_stitch_port_for_providers, peer_stitch_ports

    stitch_infos = find_stitch_port_for_providers(policy, providers)
    stitch_infos = peer_stitch_ports(stitch_infos)
    attrs = ["preference", "member-of", 'name']
    names = []

    for stitch_info in stitch_infos:
        names.append(stitch_info.stitch_port.get("name"))

        for attr in attrs:
            stitch_info.stitch_port.pop(attr, None)

        peer = stitch_info.stitch_port.get('peer', {})

        for attr in attrs:
            peer.pop(attr, None)

    import yaml
    from fabfed.util.constants import Constants

    for i, stitch_info in enumerate(stitch_infos):
        producer = stitch_info.producer
        consumer = stitch_info.consumer
        stitch_port = stitch_info.stitch_port
        c = {"config": [{Constants.NETWORK_STITCH_CONFIG: [{f"si_from_{names[i]}": {"producer": producer,
                                                                                    "consumer": consumer,
                                                                                    "stitch_port": stitch_port}}]}]}
        rep = yaml.dump(c, default_flow_style=False, sort_keys=False)
        rep = rep.replace('\n', '\n  ')
        print(rep)


def main(argv=None):
    argv = argv or sys.argv[1:]
    parser = utils.build_parser(manage_workflow=manage_workflow,
                                manage_sessions=manage_sessions,
                                display_stitch_info=display_stitch_info)
    args = parser.parse_args(argv)

    if len(args.__dict__) == 0:
        parser.print_usage()
        sys.exit(1)

    args.dispatch_func(args)


if __name__ == "__main__":
    main(sys.argv[1:])
