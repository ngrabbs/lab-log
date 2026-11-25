FROM moonbase-dtn-hdtn:smoke
COPY hdtn-configured-outducts.patch /tmp/hdtn-configured-outducts.patch
WORKDIR /src/hdtn
RUN test "$(git rev-parse HEAD)" = 7fbe90cdbe3c8c737efaacb5985f881f95fc7d2a \
    && git apply --check /tmp/hdtn-configured-outducts.patch \
    && git apply /tmp/hdtn-configured-outducts.patch \
    && cmake --build build --parallel 4 --target hdtn-one-process
