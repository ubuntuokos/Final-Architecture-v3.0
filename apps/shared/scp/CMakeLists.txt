add_library(fa3-scp-settings STATIC
    SCPSettingsService.cpp
    SCPSettingsService.h
)

target_include_directories(fa3-scp-settings
    PUBLIC
        ${CMAKE_CURRENT_SOURCE_DIR}
)

target_link_libraries(fa3-scp-settings
    PUBLIC
        Qt6::Core
)
