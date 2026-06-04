"""Pydantic request schemas for the SpreadEx web API."""

from pydantic import BaseModel, Field


class InspectRequest(BaseModel):
    subject: str
    sut_location: str
    grammar_location: str | None = None
    grammar_text: str | None = None
    grammar_mine_later: bool = False
    selected_generators: list[str] = Field(default_factory=list)
    llm_constraints: str | None = None


class RunRequest(BaseModel):
    run_id: str
    generators: list[str] = Field(default_factory=list)
    auto_select_generator: bool = False
    embedding_model: str
    prioritization_budget: int
    num_inputs_per_generator: int = 20
    run_command_template: str
    input_execution_mode: str = "file_arg"
    working_directory: str | None = None
    command_confirmed: bool = True
    openai_api_key: str | None = None
    codestral_api_key: str | None = None
