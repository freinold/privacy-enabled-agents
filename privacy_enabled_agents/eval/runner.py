"""Run evaluation with conversation tracking and error handling."""

import json
import logging
import os
from datetime import datetime
from typing import Any, Literal
from uuid import uuid4

import pandas as pd
from langchain_core.language_models import BaseChatModel, LanguageModelInput
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.runnables import Runnable
from langgraph.graph.state import CompiledStateGraph
from pydantic import BaseModel, Field, FilePath
from tqdm import tqdm
from yaml import safe_load

from privacy_enabled_agents.chat_models import PrivacyEnabledChatModel
from privacy_enabled_agents.runtime import create_agent, create_privacy_agent
from privacy_enabled_agents.topics import EvalTaskCreator
from privacy_enabled_agents.topics.base import EvalTask
from privacy_enabled_agents.topics.finance.eval import FinanceEvalTaskCreator
from privacy_enabled_agents.topics.medical.eval import MedicalEvalTaskCreator
from privacy_enabled_agents.topics.public_service.eval import PublicServiceEvalTaskCreator

from .config import EvalConfig

logger: logging.Logger = logging.getLogger(__name__)

eval_task_creator_map: dict[Literal["basic", "websearch", "finance", "medical", "public-service"], type[EvalTaskCreator]] = {
    "finance": FinanceEvalTaskCreator,
    "medical": MedicalEvalTaskCreator,
    "public-service": PublicServiceEvalTaskCreator,
}


class UserChatOutput(BaseModel):
    option: Literal["continue_conversation", "finish_successful", "finish_failed"] = Field(
        description="The option you chose. If you want to continue conversation, you need to provide a message in the other field"
    )
    message: str = Field(
        description="The message you want to send. If you chose one of the finish options, you can provide a final message here."
    )


def run_evaluation(config_filepath: FilePath) -> None:
    """Run evaluation with conversation tracking and error handling."""
    with open(config_filepath, encoding="utf-8") as file:
        config_data: Any = safe_load(file)
    eval_config: EvalConfig = EvalConfig.model_validate(config_data)

    logger.info(f"Starting evaluation with config: {config_filepath}")

    # Create privacy-enabled agent
    privacy_agent: CompiledStateGraph
    privacy_chat_model: PrivacyEnabledChatModel
    privacy_agent, privacy_chat_model = create_privacy_agent(eval_config.agent_config)

    # Create non-privacy agent for comparison (only if baseline comparison is enabled)
    non_privacy_agent: CompiledStateGraph | None = None
    if eval_config.enable_baseline_comparison:
        non_privacy_agent = create_agent(eval_config.agent_config)

    user_chat_model: BaseChatModel
    match eval_config.user_model_provider:
        case "openai":
            from langchain_openai import ChatOpenAI

            user_chat_model = ChatOpenAI(model=eval_config.user_model_name)  # type: ignore
        case "mistral":
            from langchain_mistralai import ChatMistralAI

            user_chat_model = ChatMistralAI(model=eval_config.user_model_name)  # type: ignore

    structured_user_chat_model: Runnable[LanguageModelInput, UserChatOutput] = user_chat_model.with_structured_output(schema=UserChatOutput)  # type: ignore

    results: list[dict] = []
    task_creator: type[EvalTaskCreator] | None = eval_task_creator_map.get(eval_config.agent_config.topic)
    if task_creator is None:
        raise ValueError(f"Unsupported topic: {eval_config.agent_config.topic}")

    for run in tqdm(range(eval_config.eval_runs)):
        task: EvalTask = task_creator.create_eval_task()

        # Run with privacy agent
        privacy_result = _run_single_evaluation(
            run, task, privacy_agent, structured_user_chat_model, eval_config, agent_type="privacy", chat_model=privacy_chat_model
        )
        results.append(privacy_result)

        # Run with non-privacy agent (only if baseline comparison is enabled)
        if eval_config.enable_baseline_comparison and non_privacy_agent is not None:
            non_privacy_result = _run_single_evaluation(
                run, task, non_privacy_agent, structured_user_chat_model, eval_config, agent_type="non_privacy", chat_model=None
            )
            results.append(non_privacy_result)

    result_df = pd.DataFrame(results)

    # Create main eval_results directory and subdirectory for this evaluation run
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    main_eval_dir = "eval_results"
    os.makedirs(main_eval_dir, exist_ok=True)
    output_dir = os.path.join(main_eval_dir, f"{eval_config.agent_config.topic}_{timestamp}")
    os.makedirs(output_dir, exist_ok=True)
    logger.info(f"Created output directory: {output_dir}")

    # Save results based on whether baseline comparison is enabled
    if eval_config.enable_baseline_comparison:
        # Create separate CSV files for privacy and non-privacy results
        privacy_results = result_df[result_df["agent_type"] == "privacy"]
        non_privacy_results = result_df[result_df["agent_type"] == "non_privacy"]

        privacy_filename = os.path.join(output_dir, f"eval_result_privacy_{eval_config.agent_config.topic}_{timestamp}.csv")
        baseline_filename = os.path.join(output_dir, f"eval_result_baseline_{eval_config.agent_config.topic}_{timestamp}.csv")
        combined_filename = os.path.join(output_dir, f"eval_result_combined_{eval_config.agent_config.topic}_{timestamp}.csv")

        privacy_results.to_csv(privacy_filename, index=False)
        non_privacy_results.to_csv(baseline_filename, index=False)
        result_df.to_csv(combined_filename, index=False)

        result_filenames = {
            "privacy_results": privacy_filename,
            "baseline_results": baseline_filename,
            "combined_results": combined_filename,
        }
    else:
        # Save only privacy results (default behavior)
        result_filename = os.path.join(output_dir, f"eval_result_privacy_{eval_config.agent_config.topic}_{timestamp}.csv")
        result_df.to_csv(result_filename, index=False)
        result_filenames = {"privacy_results": result_filename}

    # Write the metadata of the run to a JSON file in the output directory
    metadata: dict[str, Any] = {
        "eval_config": eval_config.model_dump_json(indent=2),
        "finish_timestamp": timestamp,
        "result_filenames": result_filenames,
        "output_directory": output_dir,
        "baseline_comparison_enabled": eval_config.enable_baseline_comparison,
    }
    metadata_filename = os.path.join(output_dir, f"eval_metadata_{eval_config.agent_config.topic}_{timestamp}.json")
    with open(metadata_filename, "w", encoding="utf-8") as file:
        json.dump(metadata, file, ensure_ascii=False, indent=2)

    logger.info(f"Evaluation complete. Results saved to: {output_dir}")


def _run_single_evaluation(
    run: int,
    task: EvalTask,
    agent: CompiledStateGraph,
    structured_user_chat_model: Runnable[LanguageModelInput, UserChatOutput],
    eval_config: EvalConfig,
    agent_type: Literal["privacy", "non_privacy"],
    chat_model: PrivacyEnabledChatModel | None = None,
) -> dict:
    """Run a single evaluation with the specified agent."""
    user_chat_messages: list[BaseMessage] = [SystemMessage(content=task["instruction"])]
    conversation_id = str(uuid4())
    finish_reason: str = "turns_exceeded"

    n_turns = 0
    while n_turns <= eval_config.max_turns:
        n_turns += 1
        logger.info(f"Run {run + 1} ({agent_type}), Turn {n_turns}")

        user_chat_output: UserChatOutput = structured_user_chat_model.invoke(user_chat_messages)

        if user_chat_output.option == "finish_failed":
            logger.error(f"Run {run + 1} ({agent_type}), Turn {n_turns}: User marked the task as failed")
            finish_reason = "finish_failed"
            break

        if user_chat_output.option == "finish_successful":
            logger.info(f"Run {run + 1} ({agent_type}), Turn {n_turns}: User marked the task as successful")
            finish_reason = "finish_successful"
            break

        logger.info(f"User: {user_chat_output.message}")

        user_chat_messages.append(AIMessage(content=user_chat_output.message))

        try:
            state = agent.invoke(
                input={"messages": [HumanMessage(content=user_chat_output.message)], **task["additional_kwargs"]},
                config={"configurable": {"thread_id": conversation_id}},
                metadata={
                    "langfuse_session_id": conversation_id,
                    "langfuse_tags": [eval_config.agent_config.topic, "eval", agent_type],
                },
            )  # type: ignore
        except Exception as e:
            logger.error(f"Error occurred during run id {run} ({agent_type}), Turn {n_turns}: {e}")
            finish_reason = "turns_exceeded"
            break

        logger.info(f"{agent_type.title()} agent: {state['messages'][-1].content}")
        user_chat_messages.append(HumanMessage(content=state["messages"][-1].content))

    return {
        "run_id": run,
        "agent_type": agent_type,
        "turns": n_turns,
        "finish_reason": finish_reason,
        "user_chat_messages": user_chat_messages,
        "privacy_agent_messages": chat_model.get_encrypted_messages(thread_id=conversation_id) if chat_model else None,
    }
