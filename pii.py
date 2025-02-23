# ruff: noqa: E402 (no import at top level) suppressed on this file as we need to inject the truststore before importing the other modules

from truststore import inject_into_ssl

inject_into_ssl()

from src.medical_detection import detect_medical
from src.pii_detection import detect_pii


def main() -> None:
    while True:
        text = input("Enter text or EXIT: ")
        if text == "EXIT":
            break
        pii_detection_results = detect_pii(texts=text)
        medical_detection_results = detect_medical(texts=text)

        print(f"{pii_detection_results = }")
        print(f"{medical_detection_results = }")


if __name__ == "__main__":
    main()
