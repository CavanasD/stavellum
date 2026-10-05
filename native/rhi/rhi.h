#pragma once
#include <cstddef>
#include <cstdint>
#define SPRHI_EXPORT extern "C" __declspec(dllexport)
struct SPRhiQuad {
    uint64_t texture_id;
    float x, y, w, h, u0, v0, u1, v1, r, g, b, a;
};
static_assert(sizeof(SPRhiQuad) == 56);
struct SPRhiBatchItem {
    const SPRhiQuad* quads;
    size_t count;
};
static_assert(sizeof(SPRhiBatchItem) == 16);
struct SPRhiFrame {
    void* owner;
    uint8_t* pixels;
    size_t size;
};
static_assert(sizeof(SPRhiFrame) == 24);
SPRHI_EXPORT uint32_t sprhi_abi_version();
SPRHI_EXPORT void* sprhi_create(int32_t width, int32_t height, uint64_t budget, const char* api);
SPRHI_EXPORT int sprhi_upload(void*, uint64_t id, int32_t w, int32_t h, int32_t stride, const uint8_t* rgba);
SPRHI_EXPORT int sprhi_remove(void*, uint64_t id);
SPRHI_EXPORT int sprhi_submit(void*, const SPRhiQuad*, size_t count, uint8_t* bgra, size_t capacity);
// Top-down BGRA pixels remain valid until owner is released, including after
// the renderer is closed. The caller must release each successful frame once.
// On failure, all frame fields are zero; a null frame pointer is rejected.
SPRHI_EXPORT int sprhi_submit_owned(void*, const SPRhiQuad*, size_t count, SPRhiFrame* frame);
// Submit 1..8 logical frames with one offscreen GPU submission. The output
// array must have count entries. For valid counts, every entry is zero on
// failure; successful entries are published together in input order.
SPRHI_EXPORT int sprhi_submit_batch_owned(void*, const SPRhiBatchItem*, size_t count, SPRhiFrame* frames);
// The frame owner has no RHI resources and can be released on any thread.
SPRHI_EXPORT void sprhi_release_frame(void* owner);
SPRHI_EXPORT const char* sprhi_report(void*);
SPRHI_EXPORT const char* sprhi_last_error(void*);
SPRHI_EXPORT int sprhi_close(void*);
