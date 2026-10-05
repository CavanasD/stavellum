cmake_minimum_required(VERSION 3.24)
project(stavellum_rhi LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_MSVC_RUNTIME_LIBRARY "MultiThreadedDLL")
find_path(VULKAN_INCLUDE_DIR vulkan/vulkan.h REQUIRED)
set(Vulkan_INCLUDE_DIR "${VULKAN_INCLUDE_DIR}")
find_package(Qt6 6.11.2 EXACT REQUIRED COMPONENTS Core Gui GuiPrivate)
add_library(stavellum_rhi SHARED rhi.cpp)
target_link_libraries(stavellum_rhi PRIVATE Qt6::Core Qt6::Gui Qt6::GuiPrivate)
target_include_directories(stavellum_rhi PRIVATE "${VULKAN_INCLUDE_DIR}")
target_compile_definitions(stavellum_rhi PRIVATE QT_NO_KEYWORDS)
if(MSVC)
  target_compile_options(stavellum_rhi PRIVATE /W4 /EHsc)
endif()
foreach(shader quad.vert quad.frag)
  add_custom_command(OUTPUT "${CMAKE_CURRENT_BINARY_DIR}/${shader}.qsb"
    COMMAND "${QSB_EXECUTABLE}" -o "${CMAKE_CURRENT_BINARY_DIR}/${shader}.qsb" "${CMAKE_CURRENT_SOURCE_DIR}/${shader}"
    DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/${shader}" VERBATIM)
endforeach()
add_custom_target(rhi_shaders DEPENDS "${CMAKE_CURRENT_BINARY_DIR}/quad.vert.qsb" "${CMAKE_CURRENT_BINARY_DIR}/quad.frag.qsb")
add_dependencies(stavellum_rhi rhi_shaders)
add_custom_command(TARGET stavellum_rhi POST_BUILD
  COMMAND ${CMAKE_COMMAND} -E copy_if_different "${CMAKE_CURRENT_BINARY_DIR}/quad.vert.qsb" "$<TARGET_FILE_DIR:stavellum_rhi>/quad.vert.qsb"
  COMMAND ${CMAKE_COMMAND} -E copy_if_different "${CMAKE_CURRENT_BINARY_DIR}/quad.frag.qsb" "$<TARGET_FILE_DIR:stavellum_rhi>/quad.frag.qsb")
