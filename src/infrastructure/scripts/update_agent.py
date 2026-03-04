from src.infrastructure.di.container import Container


def main():
    container = Container()
    agent=container.agent_adapter
    agent.update_agent_tools()
    #agent._list_agent_tools()


if __name__ == "__main__":
    main()