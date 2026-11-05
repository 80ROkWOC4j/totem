# zmk-dev-arm:3.5, matching the existing ZMK 0.3-based fork.
FROM docker.io/zmkfirmware/zmk-dev-arm@sha256:9dd48f05e5c9d3311057d114fd719d8a9dc43a5648b6fd572829b2ba05e0cd04

COPY .devcontainer/requirements-ota.txt /tmp/requirements-ota.txt
# The image is the isolated Python environment; do not install these on the host.
RUN python3 -m pip install --break-system-packages --no-cache-dir \
    --no-build-isolation --require-hashes -r /tmp/requirements-ota.txt \
    && adafruit-nrfutil version

# Bootloader upstream CI uses this compiler, independently of the Zephyr SDK.
ARG ARM_GNU_ARCHIVE=arm-gnu-toolchain-12.3.rel1-x86_64-arm-none-eabi.tar.xz
ARG ARM_GNU_SHA256=12a2815644318ebcceaf84beabb665d0924b6e79e21048452c5331a56332b309
RUN curl --fail --location --retry 3 \
    "https://developer.arm.com/-/media/Files/downloads/gnu/12.3.rel1/binrel/${ARM_GNU_ARCHIVE}" \
    -o /tmp/arm-gnu.tar.xz \
    && echo "${ARM_GNU_SHA256}  /tmp/arm-gnu.tar.xz" | sha256sum --check --strict \
    && mkdir -p /opt/arm-gnu \
    && tar -xJf /tmp/arm-gnu.tar.xz --strip-components=1 -C /opt/arm-gnu \
    && rm /tmp/arm-gnu.tar.xz
ENV PATH="/opt/arm-gnu/bin:${PATH}"

WORKDIR /workspaces/totem
