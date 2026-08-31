# syntax=docker/dockerfile:1
#
# Caddy with on-the-fly Brotli.
#
# Stock Caddy 2 ships gzip and zstd encoders only; there is no built-in Brotli.
# Brotli is not optional here: R24.1's 150 KB citizen budget is stated in
# *compressed* bytes and the CI budget test (design §10.5, task 19.5) measures
# assets at brotli quality 11. If the proxy served gzip or identity while the
# test measured brotli, the test would be measuring bytes no citizen receives.
#
# dunglas/caddy-cbrotli binds Google's reference C implementation, which is what
# makes quality 11 affordable on the fly. The pure-Go alternative
# (ueffel/caddy-brotli) is documented by its own author as unsuitable above
# level 5, so it cannot serve the quality the budget test assumes.

ARG CADDY_VERSION=2.10.2

FROM caddy:${CADDY_VERSION}-builder-alpine AS builder

# build-base for cgo, brotli-dev for the libbrotlienc/libbrotlidec headers.
RUN apk add --no-cache build-base brotli-dev

ENV CGO_ENABLED=1
RUN xcaddy build --with github.com/dunglas/caddy-cbrotli@v1.0.1

FROM caddy:${CADDY_VERSION}-alpine

# Runtime shared objects for the cgo-linked encoder.
RUN apk add --no-cache brotli-libs

COPY --from=builder /usr/bin/caddy /usr/bin/caddy

# Fail fast if the image was built without the encoder rather than silently
# falling back to gzip at runtime.
RUN caddy list-modules | grep -qx 'http.encoders.br'
