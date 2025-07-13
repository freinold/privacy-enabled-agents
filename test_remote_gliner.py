# ruff: noqa: E402 (no import at top level) suppressed on this file as we need to inject the truststore before importing the other modules

from truststore import inject_into_ssl

inject_into_ssl()

from privacy_enabled_agents.base import Entity
from privacy_enabled_agents.detection.remote_gliner import RemoteGlinerDetector


def main() -> None:
    print("Loading models...")
    pii_detector = RemoteGlinerDetector("http://localhost:8081")
    medical_detector = RemoteGlinerDetector("http://localhost:8082")
    print("Models loaded.")

    while True:
        text = input("Enter text or 'exit': ")
        if text.lower() == "exit":
            break

        pii_detection_results: list[Entity] = pii_detector.invoke(input=text)
        medical_detection_results: list[Entity] = medical_detector.invoke(input=text)

        print(f"{pii_detection_results = }")
        print(f"{medical_detection_results = }")


if __name__ == "__main__":
    main()
