"""AgentServer registration for the Sleeptown energy check action."""

from maa.agent.agent_server import AgentServer

from action.sleeptown.sleeptown_energy import SleeptownRightEnergyCheck


AgentServer.custom_action("Sleeptown_RightEnergy_Check")(
    SleeptownRightEnergyCheck
)
