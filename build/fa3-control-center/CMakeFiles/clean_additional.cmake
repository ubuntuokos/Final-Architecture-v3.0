# Additional clean files
cmake_minimum_required(VERSION 3.16)

if("${CONFIG}" STREQUAL "" OR "${CONFIG}" STREQUAL "Release")
  file(REMOVE_RECURSE
  "CMakeFiles/fa3-control-center_autogen.dir/AutogenUsed.txt"
  "CMakeFiles/fa3-control-center_autogen.dir/ParseCache.txt"
  "fa3-control-center_autogen"
  )
endif()
