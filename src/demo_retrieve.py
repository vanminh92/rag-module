"""Display real retrieved chunks as UTF-8 JSON, or use an interactive loop."""

import argparse
import json

from .retriever import retrieve


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--question", help="Bỏ trống để nhập nhiều câu hỏi trong một tiến trình")
    parser.add_argument("--top-k", type=int, default=3)
    args = parser.parse_args()
    try:
        if args.question is not None:
            print(json.dumps(retrieve(args.question, args.top_k), ensure_ascii=False, indent=2))
        else:
            while True:
                question = input("Câu hỏi (Enter để thoát): ")
                if not question.strip():
                    break
                print(json.dumps(retrieve(question, args.top_k), ensure_ascii=False, indent=2))
    except (ValueError, OSError) as exc:
        parser.exit(1, f"Lỗi: {exc}\n")
    except (EOFError, KeyboardInterrupt):
        print()


if __name__ == "__main__":
    main()
