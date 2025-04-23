from temporalio.api.export.v1 import WorkflowExecutions
from google.protobuf.json_format import MessageToJson

def protobuf_to_json(filename: str) -> str:
    """
    Accepts a filename containing a serialized temporal.api.export.v1.WorkflowExecution
    and returns a JSON string of the history

    Args:
        filename: The path to the file containing the serialized data

    Returns:
        A JSON string representing the workflow history

    Raises:
        FileNotFoundError: If the specified file does not exist.
        IOError: If there is an error reading the file.
        google.protobuf.message.DecodeError: If the file contents cannot be
                                              deserialized into a
                                              WorkflowExecution object.
    """

    workflow_execution = load_workflow_execution_from_file(filename)
    if len(workflow_execution.items) > 1:
        raise Exception("Multiple workflow histories in the file")

    work_flow = workflow_execution.items[0]
    history = work_flow.history
    return MessageToJson(history)

def load_workflow_execution_from_file(filename: str) -> WorkflowExecutions:
    """
    Accepts a filename containing a serialized
    temporal.api.export.v1.WorkflowExecution and returns the parsed object.

    Args:
        filename: The path to the file containing the serialized data.

    Returns:
        A temporal.api.export.v1.WorkflowExecutions object.

    Raises:
        FileNotFoundError: If the specified file does not exist.
        IOError: If there is an error reading the file.
        google.protobuf.message.DecodeError: If the file contents cannot be
                                              deserialized into a
                                              WorkflowExecution object.
    """
    workflow_executions = WorkflowExecutions()
    try:
        with open(filename, 'rb') as f:
            workflow_executions.ParseFromString(f.read())
        return workflow_executions
    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {filename}")
    except IOError as e:
        raise IOError(f"Error reading file: {filename} - {e}")
    except Exception as e:
        from google.protobuf.message import DecodeError
        if isinstance(e, DecodeError):
            raise DecodeError(f"Failed to deserialize WorkflowExecution from file: {filename} - {e}")
        else:
            raise Exception(f"An unexpected error occurred: {e}")

if __name__ == '__main__':
    sample_filename = "protofiles/sample.proto"
    try:
        json = protobuf_to_json(sample_filename)
        print(json)

    except Exception as e:
        print(f"Error loading WorkflowExecution: {e}")

