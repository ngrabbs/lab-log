FROM moonbase-dtn-ion:smoke
COPY ion-tcpclv4-session-gate.patch /tmp/ion-tcpclv4-session-gate.patch
WORKDIR /src/ion
RUN test "$(git rev-parse HEAD)" = b7e2c84a9b0e6f91e50d45f8946b9aa42749d93f \
    && git apply --check /tmp/ion-tcpclv4-session-gate.patch \
    && git apply /tmp/ion-tcpclv4-session-gate.patch \
    && make -j4 && make install && ldconfig
