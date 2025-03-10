# ruff: noqa: E402 (no import at top level) suppressed on this file as we need to inject the truststore before importing the other modules

from truststore import inject_into_ssl

inject_into_ssl()

from privacy_enabled_agents.detection.gliner import GlinerMedicalDetector, GlinerPIIDetector


def main() -> None:
    print("Loading models...")
    pii_detector = GlinerPIIDetector()
    medical_detector = GlinerMedicalDetector()
    print("Models loaded.")

    while True:
        text = input("Enter text or 'exit': ")
        if text.lower() == "exit":
            break

        pii_detection_results = pii_detector.detect(texts=text)
        medical_detection_results = medical_detector.detect(texts=text)

        print(f"{pii_detection_results = }")
        print(f"{medical_detection_results = }")


if __name__ == "__main__":
    main()
