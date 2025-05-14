import os
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

from api.openai_client import OpenAIClient

# Get API key from environment variables
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')

# Set key in environment (in case it's needed elsewhere in the code)
if OPENAI_API_KEY:
    os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
else:
    logger.warning("OPENAI_API_KEY not set in environment variables (.env). Some functionality may not work correctly.")

# Get configuration directory from environment variable, or use default if not set
CONFIG_DIR = os.environ.get('DEEPWIKI_CONFIG_DIR', None)

# Client class mapping
CLIENT_CLASSES = {
    "OpenAIClient": OpenAIClient
}

# Load JSON configuration file
def load_json_config(filename):
    try:
        # If environment variable is set, use the directory specified by it
        if CONFIG_DIR:
            config_path = Path(CONFIG_DIR) / filename
        else:
            # Otherwise use default directory
            config_path = Path(__file__).parent / "config" / filename
            
        logger.info(f"Loading configuration from {config_path}")
        
        if not config_path.exists():
            logger.warning(f"Configuration file {config_path} does not exist")
            return {}
            
        with open(config_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading configuration file {filename}: {str(e)}")
        return {}

# Load generator model configuration
def load_generator_config():
    generator_config = load_json_config("generator.json")
    
    # Add client class to provider
    if "providers" in generator_config:
        for provider_id, provider_config in generator_config["providers"].items():
            # Only keep OpenAI provider
            if provider_id == "openai":
                # Try to set client class from client_class
                if provider_config.get("client_class") in CLIENT_CLASSES:
                    provider_config["model_client"] = CLIENT_CLASSES[provider_config["client_class"]]
                else:
                    provider_config["model_client"] = OpenAIClient
    
    return generator_config

# Load embedder configuration
def load_embedder_config():
    embedder_config = load_json_config("embedder.json")
    
    # Process client classes
    if "embedder" in embedder_config and "client_class" in embedder_config["embedder"]:
        class_name = embedder_config["embedder"]["client_class"]
        if class_name in CLIENT_CLASSES:
            embedder_config["embedder"]["model_client"] = CLIENT_CLASSES[class_name]
        else:
            embedder_config["embedder"]["model_client"] = OpenAIClient
    
    return embedder_config

# Load repository and file filters configuration
def load_repo_config():
    return load_json_config("repo.json")

# Initialize empty configuration
configs = {}

# Load all configuration files
generator_config = load_generator_config()
embedder_config = load_embedder_config()
repo_config = load_repo_config()

# Update configuration
if generator_config:
    configs["default_provider"] = "openai"  # Always use OpenAI as default
    # Only keep the OpenAI provider
    if "providers" in generator_config and "openai" in generator_config["providers"]:
        configs["providers"] = {"openai": generator_config["providers"]["openai"]}
    else:
        configs["providers"] = {}

# Update embedder configuration
if embedder_config:
    for key in ["embedder", "retriever", "text_splitter"]:
        if key in embedder_config:
            configs[key] = embedder_config[key]

# Update repository configuration
if repo_config:
    for key in ["file_filters", "repository"]:
        if key in repo_config:
            configs[key] = repo_config[key]

def get_model_config(provider="openai", model=None):
    """
    Get configuration for the specified provider and model
    
    Parameters:
        provider (str): Model provider (only 'openai' is supported)
        model (str): Model name, or None to use default model
    
    Returns:
        dict: Configuration containing model_client, model and other parameters
    """
    # Ensure provider is openai
    if provider != "openai":
        provider = "openai"
        logger.warning(f"Only OpenAI provider is supported. Using OpenAI instead.")
    
    # Get provider configuration
    if "providers" not in configs:
        raise ValueError("Provider configuration not loaded")
        
    provider_config = configs["providers"].get(provider)
    if not provider_config:
        raise ValueError(f"Configuration for OpenAI provider not found")
    
    model_client = provider_config.get("model_client")
    if not model_client:
        model_client = OpenAIClient
    
    # If model not provided, use default model for the provider
    if not model:
        model = provider_config.get("default_model")
        if not model:
            raise ValueError(f"No default model specified for OpenAI provider")
    
    # Get model parameters (if present)
    model_params = {}
    if model in provider_config.get("models", {}):
        model_params = provider_config["models"][model]
    else:
        default_model = provider_config.get("default_model")
        if default_model and default_model in provider_config.get("models", {}):
            model_params = provider_config["models"][default_model]
    
    # Prepare configuration
    result = {
        "model_client": model_client,
        "model_kwargs": {"model": model, **model_params}
    }
    
    return result
