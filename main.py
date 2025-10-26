# main.py
import argparse
from app import create_app
from app.services.warmup import warmup

app = create_app()

def cli_warmup(limit: int, force: bool):
    with app.app_context():
        result = warmup(limit_posts=limit, force=force)
        print(
            f"WARMUP => posts_scanned={result['posts_scanned']} "
            f"media_found={result['media_found']} "
            f"cached={result['cached']} "
            f"skipped={result['skipped']} "
            f"failed={result['failed']}"
        )

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--warmup', action='store_true')
    parser.add_argument('--limit', type=int, default=20)
    parser.add_argument('--force', action='store_true')
    parser.add_argument('--port', type=int, default=8080)
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--debug', action='store_true')
    args = parser.parse_args()

    if args.warmup:
        cli_warmup(limit=args.limit, force=args.force)
    else:
        app.run(host=args.host, port=args.port, debug=args.debug)

if __name__ == "__main__":
    main()
