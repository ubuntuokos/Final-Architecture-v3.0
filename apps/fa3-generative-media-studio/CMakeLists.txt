cmake_minimum_required(VERSION 3.21)
project(fa3-generative-media-studio VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(Qt6 6.5 REQUIRED COMPONENTS Core Gui Qml Quick QuickControls2)
qt_standard_project_setup(REQUIRES 6.5)

qt_add_executable(fa3-generative-media-studio
    src/main.cpp
    src/StudioBackend.cpp
    src/StudioBackend.h
)

qt_add_qml_module(fa3-generative-media-studio
    URI org.fa3.GenerativeMediaStudio
    VERSION 1.0
    QML_FILES qml/Main.qml
)

target_link_libraries(fa3-generative-media-studio PRIVATE
    Qt6::Core Qt6::Gui Qt6::Qml Qt6::Quick Qt6::QuickControls2
)

install(TARGETS fa3-generative-media-studio RUNTIME DESTINATION bin)
