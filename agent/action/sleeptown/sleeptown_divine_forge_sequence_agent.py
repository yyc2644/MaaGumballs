"""AgentServer registration for the disabled Sleeptown divine-forge template."""

from maa.agent.agent_server import AgentServer

from action.sleeptown.sleeptown_divine_forge_sequence import (
    SleeptownDivineForgeSequenceTemplate,
)


AgentServer.custom_action("Sleeptown_DivineForge_Sequence_Template")(
    SleeptownDivineForgeSequenceTemplate
)
