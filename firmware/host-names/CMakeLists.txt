zephyr_include_directories(include)
zephyr_library()
zephyr_library_include_directories(${APPLICATION_SOURCE_DIR}/include)
zephyr_library_sources(src/behavior.c)
zephyr_library_sources_ifdef(CONFIG_TOTEM_HOST_NAMES
  src/core.c src/host_names.c src/widget.c)
