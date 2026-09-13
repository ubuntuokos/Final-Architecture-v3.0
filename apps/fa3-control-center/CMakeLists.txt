cmake_minimum_required(VERSION 3.24)
project(FA3ControlCenter VERSION 0.2.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_AUTOMOC ON)

find_package(Qt6 6.4 REQUIRED COMPONENTS Quick QuickControls2 Network)

qt_standard_project_setup(REQUIRES 6.4)

qt_add_executable(fa3-control-center
    src/main.cpp
    src/Fa3RepositoryModel.cpp
    src/Fa3RepositoryModel.h
    src/LlmfitClient.cpp
    src/LlmfitClient.h
)

set_source_files_properties(qml/Main.qml PROPERTIES QT_RESOURCE_ALIAS Main.qml)

qt_add_qml_module(fa3-control-center
    URI FA3.ControlCenter
    VERSION 1.0
    RESOURCE_PREFIX "/qt/qml"
    QML_FILES
        qml/Main.qml
)

target_link_libraries(fa3-control-center
    PRIVATE
        Qt6::Quick
        Qt6::QuickControls2
        Qt6::Network
)

install(TARGETS fa3-control-center
    RUNTIME DESTINATION libexec
)

install(FILES packaging/org.fa3.ControlCenter.desktop
    DESTINATION share/applications
)
