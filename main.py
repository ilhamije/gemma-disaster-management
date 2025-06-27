# main.py
from src.gemma_analyzer import DisasterAnalyzer
from src.damage_detector import DamageDetectionPipeline
from src.mapping_service import DisasterMap


def main():
    print("🚁 Disaster Response AI - Powered by Gemma 3n on Jetson Nano")

    # Initialize components
    analyzer = DisasterAnalyzer()
    pipeline = DamageDetectionPipeline(analyzer)
    mapper = DisasterMap()

    # Process RescueNet dataset
    print("Processing RescueNet dataset...")
    results = pipeline.process_rescuenet_dataset("./data/rescuenet")

    # Generate damage assessment map
    print("Creating damage assessment map...")
    damage_map = mapper.create_damage_map(results)
    damage_map.save("results/disaster_damage_map.html")

    # Generate summary report
    summary = generate_impact_summary(results)
    with open("results/impact_report.json", "w") as f:
        json.dump(summary, f, indent=2)

    print("✅ Analysis complete! Check results/ directory")


if __name__ == "__main__":
    main()
