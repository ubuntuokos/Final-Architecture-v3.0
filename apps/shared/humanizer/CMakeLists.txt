add_library(fa3-humanizer-shared STATIC
    HumanizerSettingsService.cpp
    HumanizerSettingsService.h
)

target_include_directories(fa3-humanizer-shared
    PUBLIC
        ${CMAKE_CURRENT_SOURCE_DIR}
)

target_link_libraries(fa3-humanizer-shared
    PUBLIC
        Qt6::Core
)
