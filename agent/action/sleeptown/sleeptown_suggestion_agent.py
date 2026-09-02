"""AgentServer registration for the Sleeptown suggestion action."""

from maa.agent.agent_server import AgentServer

from action.sleeptown.sleeptown_suggestion import (
    SleeptownSuggestionPathValidation,
)


AgentServer.custom_action("Sleeptown_Suggestion_Path_Validation")(
    SleeptownSuggestionPathValidation
)
