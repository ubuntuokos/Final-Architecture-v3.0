rule FA3_Controlled_Pickle_OS_System
{
  meta:
    description = "FA3 deny pattern for protocol-0 pickle invoking os.system"
    authority = "evidence_sensor_only"
  strings:
    $py_os_system = "cos\nsystem\n" ascii
    $posix_system = "cposix\nsystem\n" ascii
  condition:
    any of them
}

rule FA3_Controlled_Pickle_Subprocess
{
  meta:
    description = "FA3 deny pattern for obvious protocol-0 pickle subprocess entrypoints"
    authority = "evidence_sensor_only"
  strings:
    $popen = "csubprocess\nPopen\n" ascii
    $call = "csubprocess\ncall\n" ascii
  condition:
    any of them
}
