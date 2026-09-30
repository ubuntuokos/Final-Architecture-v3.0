cmake_minimum_required(VERSION 3.24)
project(FA3Humanizer VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_AUTOMOC ON)

find_package(Qt6 6.4 REQUIRED COMPONENTS Core Quick QuickControls2)
qt_standard_project_setup(REQUIRES 6.4)

add_subdirectory("../shared/humanizer" "${CMAKE_CURRENT_BINARY_DIR}/shared-humanizer")

qt_add_executable(fa3-humanizer
    src/main.cpp
)

set_source_files_properties(qml/Main.qml PROPERTIES QT_RESOURCE_ALIAS Main.qml)
set_source_files_properties(
    "${CMAKE_CURRENT_SOURCE_DIR}/../shared/humanizer/qml/HumanizerSettingsPanel.qml"
    PROPERTIES QT_RESOURCE_ALIAS HumanizerSettingsPanel.qml
)

qt_add_qml_module(fa3-humanizer
    URI FA3.Humanizer
    VERSION 1.0
    RESOURCE_PREFIX "/qt/qml"
    QML_FILES
        qml/Main.qml
        "../shared/humanizer/qml/HumanizerSettingsPanel.qml"
)

target_link_libraries(fa3-humanizer
    PRIVATE
        Qt6::Core
        Qt6::Quick
        Qt6::QuickControls2
        fa3-humanizer-shared
)

install(TARGETS fa3-humanizer RUNTIME DESTINATION libexec)
install(FILES packaging/org.fa3.Humanizer.desktop DESTINATION share/applications)
