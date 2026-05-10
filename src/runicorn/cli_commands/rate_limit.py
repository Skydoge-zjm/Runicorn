from __future__ import annotations

import json
from typing import Any, Callable


def handle_rate_limit(
    args: Any,
    *,
    get_rate_limit_config: Callable[[], dict[str, Any]],
    save_rate_limit_config: Callable[[dict[str, Any]], None],
    input_fn: Callable[[str], str] = input,
) -> int:
    action = args.action

    if action == "show":
        config = get_rate_limit_config()
        print(json.dumps(config, indent=2))
        return 0

    if action == "list":
        config = get_rate_limit_config()
        default = config.get("default", {})
        print("Default:")
        print(f"  {default.get('max_requests', 6000)}/{default.get('window_seconds', 60)}s")

        endpoints = config.get("endpoints", {})
        if endpoints:
            print("\nEndpoints:")
            for endpoint, endpoint_config in sorted(endpoints.items()):
                desc = endpoint_config.get("description", "")
                desc_str = f" - {desc}" if desc else ""
                burst = endpoint_config.get("burst_size")
                burst_str = f" (burst: {burst})" if burst else ""
                print(
                    f"  {endpoint}: {endpoint_config.get('max_requests')}/"
                    f"{endpoint_config.get('window_seconds')}s{burst_str}{desc_str}"
                )
        else:
            print("\nNo endpoint-specific limits configured.")
        return 0

    if action == "get":
        if not args.endpoint:
            print("Error: --endpoint is required for 'get' action")
            return 1

        config = get_rate_limit_config()
        endpoint_config = config.get("endpoints", {}).get(args.endpoint)

        if endpoint_config:
            print(f"Endpoint: {args.endpoint}")
            print(f"  Max Requests: {endpoint_config.get('max_requests')}")
            print(f"  Window: {endpoint_config.get('window_seconds')}s")
            print(f"  Burst Size: {endpoint_config.get('burst_size', 'None')}")
            if "description" in endpoint_config:
                print(f"  Description: {endpoint_config.get('description')}")
        else:
            default_config = config.get("default", {})
            print(f"Endpoint: {args.endpoint} (using default)")
            print(f"  Max Requests: {default_config.get('max_requests', 6000)}")
            print(f"  Window: {default_config.get('window_seconds', 60)}s")
            print(f"  Burst Size: {default_config.get('burst_size', 'None')}")
        return 0

    if action == "set":
        if not args.endpoint or args.max_requests is None:
            print("Error: --endpoint and --max-requests are required for 'set' action")
            return 1

        config = get_rate_limit_config()
        endpoints = config.setdefault("endpoints", {})
        endpoint_config: dict[str, Any] = {
            "max_requests": args.max_requests,
            "window_seconds": args.window,
            "burst_size": args.burst,
        }
        if args.description:
            endpoint_config["description"] = args.description

        endpoints[args.endpoint] = endpoint_config
        save_rate_limit_config(config)

        print(f"Updated rate limit for {args.endpoint}")
        print(f"  Max Requests: {args.max_requests}/{args.window}s")
        if args.burst:
            print(f"  Burst Size: {args.burst}")
        return 0

    if action == "remove":
        if not args.endpoint:
            print("Error: --endpoint is required for 'remove' action")
            return 1

        config = get_rate_limit_config()
        if "endpoints" in config and args.endpoint in config["endpoints"]:
            del config["endpoints"][args.endpoint]
            save_rate_limit_config(config)
            print(f"Removed rate limit for {args.endpoint}")
        else:
            print(f"No specific rate limit found for {args.endpoint}")
        return 0

    if action == "settings":
        config = get_rate_limit_config()
        settings = config.setdefault("settings", {})

        if args.enable:
            settings["enable_rate_limiting"] = True
        elif args.disable:
            settings["enable_rate_limiting"] = False

        if args.log_violations:
            settings["log_violations"] = True
        elif args.no_log_violations:
            settings["log_violations"] = False

        if args.whitelist_localhost:
            settings["whitelist_localhost"] = True
        elif args.no_whitelist_localhost:
            settings["whitelist_localhost"] = False

        save_rate_limit_config(config)

        print("Updated settings:")
        print(f"  Rate Limiting: {'Enabled' if settings.get('enable_rate_limiting', True) else 'Disabled'}")
        print(f"  Log Violations: {'Yes' if settings.get('log_violations', True) else 'No'}")
        print(f"  Whitelist Localhost: {'Yes' if settings.get('whitelist_localhost', False) else 'No'}")
        return 0

    if action == "reset":
        confirm = input_fn("Reset to default configuration? [y/N] ")
        if confirm.lower() != "y":
            print("Cancelled.")
            return 0

        default_config = {
            "_comment": "Rate limits are high for local-only API with no internet exposure",
            "default": {
                "max_requests": 6000,
                "window_seconds": 60,
                "burst_size": None,
                "description": "Default rate limit - very permissive for local use",
            },
            "endpoints": {},
            "settings": {
                "enable_rate_limiting": False,
                "log_violations": True,
                "whitelist_localhost": False,
                "custom_headers": {
                    "rate_limit_header": "X-RateLimit-Limit",
                    "rate_limit_remaining_header": "X-RateLimit-Remaining",
                    "rate_limit_reset_header": "X-RateLimit-Reset",
                },
            },
        }
        save_rate_limit_config(default_config)
        print("Reset to default configuration")
        return 0

    if action == "validate":
        try:
            config = get_rate_limit_config()
            assert isinstance(config, dict), "Configuration must be a dictionary"

            if "default" in config:
                default = config["default"]
                assert isinstance(default.get("max_requests"), int), "max_requests must be an integer"
                assert isinstance(default.get("window_seconds"), int), "window_seconds must be an integer"
                assert default.get("max_requests") > 0, "max_requests must be positive"
                assert default.get("window_seconds") > 0, "window_seconds must be positive"

            if "endpoints" in config:
                endpoints = config["endpoints"]
                assert isinstance(endpoints, dict), "endpoints must be a dictionary"
                for endpoint, endpoint_config in endpoints.items():
                    assert endpoint.startswith("/"), f"Endpoint '{endpoint}' must start with /"
                    assert isinstance(endpoint_config.get("max_requests"), int), (
                        f"{endpoint}: max_requests must be an integer"
                    )
                    assert isinstance(endpoint_config.get("window_seconds"), int), (
                        f"{endpoint}: window_seconds must be an integer"
                    )
                    assert endpoint_config.get("max_requests") > 0, (
                        f"{endpoint}: max_requests must be positive"
                    )
                    assert endpoint_config.get("window_seconds") > 0, (
                        f"{endpoint}: window_seconds must be positive"
                    )

            print("Configuration is valid")
            return 0
        except AssertionError as e:
            print(f"Configuration error: {e}")
            return 1
        except Exception as e:
            print(f"Failed to validate configuration: {e}")
            return 1

    return 0

