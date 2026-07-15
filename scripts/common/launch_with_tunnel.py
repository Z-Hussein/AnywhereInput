import argparse
import subprocess
import sys

def main():
    parser = argparse.ArgumentParser(description="Launch AnywhereInput with tunnel")
    parser.add_argument("--provider", choices=["cloudflare", "pinggy", "zrok2"], required=True)
    args = parser.parse_args()

    cmd = [sys.executable, "-m", "anywhereinput.server", "--tunnel", args.provider]
    subprocess.run(cmd)

if __name__ == "__main__":
    main()
