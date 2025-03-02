import os
import yaml
from typing import Dict, List, Any, Optional, Union
from smolagents import CodeAgent, OpenAIServerModel, LiteLLMModel, HfApiModel
from smolagents.models import Model

def load_template(template_path: Optional[str] = None) -> Dict:
    """
    Load a YAML template for agent prompts.
    
    Args:
        template_path: Path to the YAML template file. If None, uses the default template.
        
    Returns:
        Dict containing the template configuration.
    """
    if template_path is None:
        # Use the default template
        template_path = os.path.join(os.path.dirname(__file__), "../templates/code-template.yaml")
    
    with open(template_path, "r") as f:
        return yaml.safe_load(f)

def create_model(
    model_id: str = "gemini-2.0-flash",
    api_key: Optional[str] = None,
    api_base: Optional[str] = "https://generativelanguage.googleapis.com/v1beta/openai/",
) -> Model:
    """
    Create a model instance based on the model_id.
    
    Args:
        model_id: The ID of the model to use.
        api_key: API key for the model provider. If None, will try to get from environment.
        api_base: Base URL for the API.
        
    Returns:
        A configured model instance.
    """
    # If API key not provided, try to get from environment
    if api_key is None:
        if "GEMINI_API_KEY" in os.environ and model_id.startswith("gemini"):
            api_key = os.environ.get("GEMINI_API_KEY")
        elif "OPENAI_API_KEY" in os.environ and model_id.startswith(("gpt", "text-")):
            api_key = os.environ.get("OPENAI_API_KEY")
        elif "HF_API_KEY" in os.environ:
            api_key = os.environ.get("HF_API_KEY")
    
    # Create model based on model_id prefix
    if model_id.startswith("gemini"):
        return OpenAIServerModel(
            model_id=model_id,
            api_key=api_key,
            api_base=api_base,
        )
    elif model_id.startswith(("gpt", "text-")):
        return OpenAIServerModel(
            model_id=model_id,
            api_key=api_key,
        )
    else:
        # Assume it's a HuggingFace model
        return HfApiModel(model_id=model_id, token=api_key)

def create_analysis_agent(
    model: Optional[Model] = None,
    template_path: Optional[str] = None,
    tools: Optional[List[Any]] = None,
    name: str = "analysis_agent",
    description: str = "This agent is responsible for analyzing the codebase and determining what files are causing the issue."
) -> CodeAgent:
    """
    Create an analysis agent for exploring and understanding a codebase.
    
    Args:
        model: A pre-configured model instance. If provided, model_id, api_key, and api_base are ignored.
        template_path: Path to the YAML template file. If None, uses the default template.
        tools: List of tools to provide to the agent. If None, uses repository_querier tools.
        name: Name of the agent.
        description: Description of the agent's purpose.
        
    Returns:
        A configured CodeAgent instance.
    """
    # Load template
    template = load_template(template_path)
    
    # If tools not provided, use repository_querier
    if tools is None:
        from kowinski.tools.code_analysis import repository_querier
        tools = repository_querier().values()
    
    # Create model if not provided
    if model is None:
        raise ValueError("Model must be provided")
    
    # Create and return the agent
    return CodeAgent(
        tools=tools,
        model=model,
        prompt_templates=template,
        name=name,
        description=description
    )

def create_code_agent(
    model: Optional[Model] = None,
    template_path: Optional[str] = None,
    tools: Optional[List[Any]] = None,
    analysis_agent: Optional[CodeAgent] = None,
) -> CodeAgent:
    """
    Create a main code agent that can use an analysis agent.
    
    Args:
        model: A pre-configured model instance. If provided, model_id, api_key, and api_base are ignored.
        model_id: The ID of the model to use if model is not provided.
        api_key: API key for the model provider if model is not provided.
        api_base: Base URL for the API if model is not provided.
        template_path: Path to the YAML template file. If None, uses the default template.
        tools: List of tools to provide to the agent.
        analysis_agent: Optional analysis agent to include as a managed agent.
        
    Returns:
        A configured CodeAgent instance.
    """
    # Load template
    template = load_template(template_path)
    
    # Create model if not provided
    if model is None:
        raise ValueError("Model must be provided")
    
    # Create managed agents list
    managed_agents = []
    if analysis_agent:
        managed_agents.append(analysis_agent)
    
    # Create and return the agent
    return CodeAgent(
        tools=tools if tools is not None else [],
        model=model,
        prompt_templates=template,
        managed_agents=managed_agents,
    ) 