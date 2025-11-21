"""
Test script for CConfig class
"""

from core.CConfig import CConfig

def test_config():
    """Test configuration loading"""
    print("=" * 60)
    print("Testing CConfig Class")
    print("=" * 60)

    try:
        # Load configuration
        config = CConfig("config.yaml")
        print("✅ Configuration loaded successfully!\n")

        # Display configuration
        print(config)
        print("\n" + "-" * 60)
        # Test backend-specific settings
        print("Backend Configuration:")
        print(f"  Total tokens configured: {len(config.tokens)}")
        if config.tokens:
            primary = config.get_primary_token()
            print(f"  Primary token: {primary.token[:10]}...")
            print(f"  Endpoint: {primary.endpoint}")
            print(f"  Model: {primary.modelName}")
            print(f"  Stream enabled: {primary.stream}")

        print("\n" + "-" * 60)

        # Test common settings
        print("Common Configuration:")
        print(f"  Target language: {config.language}")
        print(f"  Input path: {config.inputPath}")
        print(f"  Input type: {config.inputType}")
        print(f"  Workers per project: {config.workersPerProject}")

        print("\n" + "-" * 60)

        # Test GPT settings
        print("GPT Configuration:")
        print(f"  Batch size: {config.gpt.numPerRequestTranslate}")
        print(f"  Context window: {config.gpt.contextNum}")
        print(f"  Temperature: {config.gpt.temperature}")
        print(f"  Frequency penalty: {config.gpt.frequency_penalty}")

        print("\n" + "-" * 60)

        # Test to_dict()
        print("\nExport to dictionary:")
        config_dict = config.to_dict()
        print(f"  Keys: {list(config_dict.keys())}")

        print("\n" + "=" * 60)
        print("✅ All tests passed!")
        print("=" * 60)

    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
    except ValueError as e:
        print(f"❌ Validation Error: {e}")
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_config()
