#include "rhi.h"
#include <QtCore/QFile>
#include <QtCore/QJsonDocument>
#include <QtCore/QJsonObject>
#include <QtCore/QThread>
#include <QtGui/QGuiApplication>
#include <QtGui/QImage>
#include <QtGui/QVulkanInstance>
#include <rhi/qrhi.h>
#include <rhi/qshader.h>
#define NOMINMAX
#include <Windows.h>
#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstring>
#include <limits>
#include <memory>
#include <emmintrin.h>
#include <stdexcept>
#include <unordered_map>
#include <vector>

namespace {
using Clock = std::chrono::steady_clock;
constexpr size_t MaxBatchFrames = 8;
double elapsed(Clock::time_point start) { return std::chrono::duration<double>(Clock::now() - start).count(); }
thread_local QByteArray lastError;
void require(bool condition, const char* message) { if (!condition) throw std::runtime_error(message); }
struct Texture {
    std::unique_ptr<QRhiTexture> image;
    std::unique_ptr<QRhiShaderResourceBindings> bindings;
    QImage pending;
    uint64_t bytes = 0;
};
struct Vertex { float x, y, u, v, r, g, b, a; };

void rgbaToBgra(const uint8_t* input, uint8_t* output, size_t pixelCount) {
    size_t x = 0;
    const __m128i gaMask = _mm_set1_epi32(static_cast<int>(0xff00ff00u));
    const __m128i rbMask = _mm_set1_epi32(0x00ff00ff);
    // SSE2 is part of the Windows x64 baseline. Four pixels per iteration;
    // unaligned loads/stores also support an in-place conversion.
    for (; x + 4 <= pixelCount; x += 4) {
        const __m128i pixels = _mm_loadu_si128(reinterpret_cast<const __m128i*>(input + 4*x));
        const __m128i rb = _mm_and_si128(pixels, rbMask);
        const __m128i swapped = _mm_or_si128(_mm_and_si128(pixels, gaMask),
            _mm_or_si128(_mm_slli_epi32(rb, 16), _mm_srli_epi32(rb, 16)));
        _mm_storeu_si128(reinterpret_cast<__m128i*>(output + 4*x), swapped);
    }
    for (; x < pixelCount; ++x) {
        // Retain both channels before writing so input may equal output.
        const uint8_t red = input[4*x], blue = input[4*x+2];
        output[4*x] = blue; output[4*x+1] = input[4*x+1];
        output[4*x+2] = red; output[4*x+3] = input[4*x+3];
    }
}

QString moduleDirectory() {
    HMODULE module = nullptr;
    require(GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
        reinterpret_cast<LPCWSTR>(&sprhi_abi_version), &module), "Cannot locate RHI DLL");
    wchar_t path[32768];
    DWORD length = GetModuleFileNameW(module, path, 32768);
    require(length && length < 32768, "Cannot locate RHI shader directory");
    QString filename = QString::fromWCharArray(path, int(length));
    return filename.left(filename.lastIndexOf('\\') + 1);
}
QShader shader(const QString& name) {
    QFile file(moduleDirectory() + name);
    require(file.open(QIODevice::ReadOnly), "Cannot load RHI shader package");
    QShader result = QShader::fromSerialized(file.readAll());
    require(result.isValid(), "Invalid RHI shader package");
    return result;
}

struct Renderer {
    int width, height;
    uint64_t budget, textureBytes = 0, texturePeak = 0;
    Qt::HANDLE thread = QThread::currentThreadId();
    QByteArray api, json;
    std::unique_ptr<QVulkanInstance> instance;
    std::unique_ptr<QRhi> rhi;
    std::unique_ptr<QRhiTexture> resolve;
    std::unique_ptr<QRhiTexture> msaa;
    std::unique_ptr<QRhiRenderPassDescriptor> pass;
    std::unique_ptr<QRhiTextureRenderTarget> target;
    std::unique_ptr<QRhiSampler> sampler;
    std::unique_ptr<QRhiGraphicsPipeline> pipeline;
    std::unique_ptr<QRhiBuffer> vertices;
    std::unordered_map<uint64_t, Texture> textures;
    QRhiTexture::Format outputFormat = QRhiTexture::RGBA8;
    int vertexCapacity = 0;
    bool timestamps = false;
    bool failed = false;
    uint64_t frames = 0;
    uint64_t ownedFrames = 0, copiedFrames = 0;
    uint64_t submissions = 0;
    std::array<uint64_t, MaxBatchFrames> batchHistogram{};
    size_t batchPeak = 0;
    uint64_t outputPeak = 0, stagingPeak = 0, cpuReadbackPeak = 0;
    // Qt retains pointers to these results while readbacks are pending. They
    // must also survive a failed endOffscreenFrame until QRhi is destroyed.
    std::array<QRhiReadbackResult, MaxBatchFrames> readbackResults;
    double uploadSeconds = 0, submitSeconds = 0, readbackSeconds = 0, copySeconds = 0;
    double inplaceConversionSeconds = 0;
    double gpuSeconds = 0, prepareSeconds = 0, beginFrameSeconds = 0;
    uint64_t gpuSamples = 0, uploadedBytes = 0;

    Renderer(int w, int h, uint64_t b, const char* requested) : width(w), height(h), budget(b), api(requested) {
        require(QGuiApplication::instance(), "Create QApplication through PySide6 before creating RHI");
        require(QByteArray(qVersion()) == "6.11.2", "RHI DLL requires exactly Qt 6.11.2");
        require(width > 0 && height > 0 && width <= 32768 && height <= 32768, "Invalid frame dimensions");
        QRhi::Flags flags;
        if (qEnvironmentVariableIntValue("STAVELLUM_RHI_TIMESTAMPS")) flags |= QRhi::EnableTimestamps;
        if (api == "vulkan") {
            instance = std::make_unique<QVulkanInstance>();
            instance->setExtensions(QRhiVulkanInitParams::preferredInstanceExtensions());
            instance->setFlags(QVulkanInstance::NoDebugOutputRedirect);
            require(instance->create(), "Cannot create Vulkan instance");
            QRhiVulkanInitParams params;
            params.inst = instance.get();
            const auto adapters = QRhi::enumerateAdapters(QRhi::Vulkan, &params);
            QRhiAdapter* chosen = nullptr;
            const QByteArray preferred = qgetenv("STAVELLUM_RHI_GPU");
            for (auto* adapter : adapters) {
                auto info = adapter->info();
                if ((!preferred.isEmpty() && info.deviceName.contains(preferred)) ||
                    (preferred.isEmpty() && info.deviceType == QRhiDriverInfo::DiscreteDevice)) {
                    chosen = adapter;
                    break;
                }
            }
            if (!preferred.isEmpty() && !chosen) { qDeleteAll(adapters); throw std::runtime_error("Requested Vulkan GPU unavailable"); }
            rhi.reset(QRhi::create(QRhi::Vulkan, &params, flags, nullptr, chosen));
            qDeleteAll(adapters);
        } else throw std::runtime_error("RHI API must be vulkan");
        require(bool(rhi), "Cannot initialize requested RHI backend");
        const auto info = rhi->driverInfo();
        require(info.deviceType != QRhiDriverInfo::CpuDevice, "Vulkan GPU uses a software device");
        require(rhi->supportedSampleCounts().contains(4), "Requested RHI backend cannot provide 4xMSAA");
        timestamps = bool(flags & QRhi::EnableTimestamps) && rhi->isFeatureSupported(QRhi::Timestamps);
        const QRhiTexture::Flags outputFlags = QRhiTexture::RenderTarget | QRhiTexture::UsedAsTransferSource;
        if (!qEnvironmentVariableIntValue("STAVELLUM_RHI_RGBA_READBACK")
            && rhi->isTextureFormatSupported(QRhiTexture::BGRA8, outputFlags))
            outputFormat = QRhiTexture::BGRA8;
        resolve.reset(rhi->newTexture(outputFormat, QSize(width, height), 1, outputFlags));
        require(resolve->create(), "Cannot allocate resolve texture");
        // Vulkan requires the multisample and resolve attachment formats to match.
        // Unlike a color renderbuffer's hidden backing texture, a texture is
        // explicitly tracked for write-after-write hazards between batch passes.
        msaa.reset(rhi->newTexture(outputFormat, QSize(width, height), 4, outputFlags));
        require(msaa->create(), "Cannot allocate 4xMSAA color buffer");
        QRhiColorAttachment attachment(msaa.get());
        attachment.setResolveTexture(resolve.get());
        target.reset(rhi->newTextureRenderTarget(QRhiTextureRenderTargetDescription(attachment)));
        pass.reset(target->newCompatibleRenderPassDescriptor());
        target->setRenderPassDescriptor(pass.get());
        require(target->create(), "Cannot create RHI render target");
        sampler.reset(rhi->newSampler(QRhiSampler::Linear, QRhiSampler::Linear, QRhiSampler::None,
            QRhiSampler::ClampToEdge, QRhiSampler::ClampToEdge));
        require(sampler->create(), "Cannot create RHI sampler");
        // Texture zero is a white texel shared by all solid rectangles.
        const uint8_t white[4] = {255, 255, 255, 255};
        upload(0, 1, 1, 4, white);
        pipeline.reset(rhi->newGraphicsPipeline());
        pipeline->setShaderStages({{QRhiShaderStage::Vertex, shader("quad.vert.qsb")},
                                  {QRhiShaderStage::Fragment, shader("quad.frag.qsb")}});
        QRhiVertexInputLayout layout;
        layout.setBindings({QRhiVertexInputBinding(sizeof(Vertex))});
        layout.setAttributes({
            QRhiVertexInputAttribute(0, 0, QRhiVertexInputAttribute::Float2, 0),
            QRhiVertexInputAttribute(0, 1, QRhiVertexInputAttribute::Float2, 2 * sizeof(float)),
            QRhiVertexInputAttribute(0, 2, QRhiVertexInputAttribute::Float4, 4 * sizeof(float))});
        pipeline->setVertexInputLayout(layout);
        pipeline->setShaderResourceBindings(textures.at(0).bindings.get());
        pipeline->setRenderPassDescriptor(pass.get());
        pipeline->setSampleCount(4);
        pipeline->setCullMode(QRhiGraphicsPipeline::None);
        QRhiGraphicsPipeline::TargetBlend blend;
        blend.enable = true;
        blend.srcColor = blend.srcAlpha = QRhiGraphicsPipeline::One;
        blend.dstColor = blend.dstAlpha = QRhiGraphicsPipeline::OneMinusSrcAlpha;
        pipeline->setTargetBlends({blend});
        require(pipeline->create(), "Cannot create RHI graphics pipeline");
        uploadSeconds = 0;
        uploadedBytes = 0;
    }
    void check() const {
        require(thread == QThread::currentThreadId(), "RHI objects must be used on their creating thread");
        require(!failed, "RHI renderer failed; close it and create a new instance");
    }
    void upload(uint64_t id, int w, int h, int stride, const uint8_t* bytes) {
        check();
        require(bytes && w > 0 && h > 0 && w <= rhi->resourceLimit(QRhi::TextureSizeMax) && h <= rhi->resourceLimit(QRhi::TextureSizeMax), "Invalid texture size");
        require(int64_t(stride) >= int64_t(w) * 4, "Invalid texture stride");
        require(!textures.contains(id), "Texture ID already uploaded");
        auto tick = Clock::now();
        Texture texture;
        texture.image.reset(rhi->newTexture(QRhiTexture::RGBA8, QSize(w, h)));
        require(texture.image->create(), "Cannot allocate RHI texture");
        texture.bindings.reset(rhi->newShaderResourceBindings());
        texture.bindings->setBindings({QRhiShaderResourceBinding::sampledTexture(0, QRhiShaderResourceBinding::FragmentStage,
            texture.image.get(), sampler.get())});
        require(texture.bindings->create(), "Cannot create texture bindings");
        texture.pending = QImage(bytes, w, h, stride, QImage::Format_RGBA8888_Premultiplied).copy();
        require(!texture.pending.isNull(), "Cannot retain texture upload pixels");
        texture.bytes = uint64_t(w) * h * 4;
        textureBytes += texture.bytes;
        texturePeak = std::max(texturePeak, textureBytes);
        uploadedBytes += texture.bytes;
        textures.emplace(id, std::move(texture));
        uploadSeconds += elapsed(tick);
    }
    void remove(uint64_t id) {
        check();
        require(id != 0, "Cannot delete the solid white texture");
        if (auto item = textures.find(id); item != textures.end()) {
            textureBytes -= item->second.bytes;
            textures.erase(item);
        }
    }
    void readback(const SPRhiBatchItem* items, size_t frameCount) {
        check();
        require(frameCount >= 1 && frameCount <= MaxBatchFrames, "Batch frame count must be between 1 and 8");
        require(items, "Null batch item array");
        auto tick = Clock::now();
        size_t quadCount = 0;
        for (size_t index = 0; index < frameCount; ++index) {
            require(items[index].count == 0 || items[index].quads, "Null quad array");
            require(items[index].count <= 1000000, "Too many frame commands");
            quadCount += items[index].count;
        }
        require(quadCount <= size_t(std::numeric_limits<int>::max()) / (6 * sizeof(Vertex)), "Batch vertex buffer is too large");
        std::vector<Vertex> data;
        data.reserve(quadCount * 6);
        std::array<size_t, MaxBatchFrames> firstVertices{};
        QMatrix4x4 correction = rhi->clipSpaceCorrMatrix();
        auto vertex = [&](const SPRhiQuad& q, float x, float y, float u, float v) {
            const auto p = correction * QVector4D(2 * x / width - 1, 1 - 2 * y / height, 0, 1);
            return Vertex{p.x(), p.y(), u, v, q.r, q.g, q.b, q.a};
        };
        for (size_t index = 0; index < frameCount; ++index) {
            firstVertices[index] = data.size();
            for (size_t i = 0; i < items[index].count; ++i) {
                const auto& q = items[index].quads[i];
                require(textures.contains(q.texture_id), "Frame refers to missing texture");
                require(q.w >= 0 && q.h >= 0 && std::isfinite(q.x) && std::isfinite(q.y) && std::isfinite(q.w) && std::isfinite(q.h), "Invalid quad geometry");
                for (float value : {q.u0, q.v0, q.u1, q.v1, q.r, q.g, q.b, q.a}) require(std::isfinite(value), "Invalid quad attribute");
                auto a = vertex(q, q.x, q.y, q.u0, q.v0);
                auto b = vertex(q, q.x + q.w, q.y, q.u1, q.v0);
                auto c = vertex(q, q.x + q.w, q.y + q.h, q.u1, q.v1);
                auto d = vertex(q, q.x, q.y + q.h, q.u0, q.v1);
                data.insert(data.end(), {a, b, c, a, c, d});
            }
            readbackResults[index] = {};
        }
        const int required = int(std::max(size_t(1), data.size()) * sizeof(Vertex));
        if (required > vertexCapacity) {
            auto candidate = std::unique_ptr<QRhiBuffer>(rhi->newBuffer(QRhiBuffer::Dynamic, QRhiBuffer::VertexBuffer, required));
            require(candidate->create(), "Cannot create vertex buffer");
            // A failed preframe allocation must leave the previous valid
            // buffer and its matching capacity available for a later frame.
            vertices = std::move(candidate);
            vertexCapacity = required;
        }
        prepareSeconds += elapsed(tick);
        QRhiCommandBuffer* cb = nullptr;
        tick = Clock::now();
        require(rhi->beginOffscreenFrame(&cb) == QRhi::FrameOpSuccess, "Cannot begin RHI offscreen frame");
        beginFrameSeconds += elapsed(tick);
        // Any failure after frame start makes the instance unusable: reusing
        // partially submitted resources after a device error is unsafe.
        failed = true;
        tick = Clock::now();
        auto* updates = rhi->nextResourceUpdateBatch();
        for (auto& [id, texture] : textures) {
            if (!texture.pending.isNull()) {
                updates->uploadTexture(texture.image.get(), texture.pending);
                texture.pending = {};
            }
        }
        if (!data.empty()) updates->updateDynamicBuffer(vertices.get(), 0, int(data.size() * sizeof(Vertex)), data.data());
        const QRhiCommandBuffer::VertexInput binding(vertices.get(), 0);
        for (size_t index = 0; index < frameCount; ++index) {
            cb->beginPass(target.get(), QColor(0, 0, 0, 255), {1.0f, 0}, index == 0 ? updates : nullptr);
            cb->setGraphicsPipeline(pipeline.get());
            cb->setViewport(QRhiViewport(0, 0, float(width), float(height)));
            cb->setVertexInput(0, 1, &binding);
            // Every pass uses its own vertex range: dynamic host updates made
            // later within one QRhi frame may otherwise overwrite earlier draws.
            const auto* quads = items[index].quads;
            const size_t count = items[index].count;
            // Merge only adjacent textures, preserving source-over draw order.
            for (size_t first = 0; first < count;) {
                size_t end = first + 1;
                while (end < count && quads[end].texture_id == quads[first].texture_id) ++end;
                cb->setShaderResources(textures.at(quads[first].texture_id).bindings.get());
                cb->draw(int((end - first) * 6), 1, int(firstVertices[index] + first * 6));
                first = end;
            }
            auto* readback = rhi->nextResourceUpdateBatch();
            readback->readBackTexture(QRhiReadbackDescription(resolve.get()), &readbackResults[index]);
            // Copy this resolve before the next pass clears and overwrites it.
            cb->endPass(readback);
        }
        submitSeconds += elapsed(tick);
        tick = Clock::now();
        const auto status = rhi->endOffscreenFrame();
        readbackSeconds += elapsed(tick);
        require(status == QRhi::FrameOpSuccess, "Cannot finish RHI frame");
        ++submissions;
        ++batchHistogram[frameCount - 1];
        batchPeak = std::max(batchPeak, frameCount);
        const uint64_t batchBytes = frameCount * uint64_t(width) * height * 4;
        outputPeak = std::max(outputPeak, batchBytes);
        stagingPeak = std::max(stagingPeak, batchBytes);
        cpuReadbackPeak = std::max(cpuReadbackPeak, batchBytes);
        for (size_t index = 0; index < frameCount; ++index) {
            const auto& result = readbackResults[index];
            require(result.pixelSize == QSize(width, height) && result.data.size() == qsizetype(width) * height * 4, "Unexpected RHI readback size");
            require(result.format == outputFormat, "Unexpected RHI readback format");
        }
        if (timestamps) {
            const double seconds = cb->lastCompletedGpuTime();
            if (seconds > 0) { gpuSeconds += seconds; ++gpuSamples; }
        }
    }
    void submit(const SPRhiQuad* quads, size_t count, uint8_t* output, size_t capacity) {
        check();
        require(output && capacity >= size_t(width) * height * 4, "Output pixel buffer is too small");
        const SPRhiBatchItem item{quads, count};
        readback(&item, 1);
        const QByteArray pixels = std::move(readbackResults[0].data);
        const auto tick = Clock::now();
        const auto* input = reinterpret_cast<const uint8_t*>(pixels.constData());
        if (outputFormat == QRhiTexture::BGRA8) {
            // Native BGRA readback needs no per-pixel channel conversion.
            std::memcpy(output, input, size_t(width) * height * 4);
        } else {
            // RGBA8 is always supported; keep it as a format fallback.
            rgbaToBgra(input, output, size_t(width) * height);
        }
        copySeconds += elapsed(tick);
        ++frames;
        ++copiedFrames;
        cpuReadbackPeak = std::max(cpuReadbackPeak, uint64_t(width) * height * 8);
        failed = false;
    }
    void submitOwned(const SPRhiQuad* quads, size_t count, SPRhiFrame* frame) {
        const SPRhiBatchItem item{quads, count};
        submitBatchOwned(&item, 1, frame);
    }
    void submitBatchOwned(const SPRhiBatchItem* items, size_t frameCount, SPRhiFrame* output) {
        check();
        require(output, "Null output frame");
        readback(items, frameCount);
        // This owner contains only CPU bytes: it may outlive this renderer and
        // be destroyed on the writer thread after the last QImage releases it.
        std::array<std::unique_ptr<QByteArray>, MaxBatchFrames> pixels;
        std::array<SPRhiFrame, MaxBatchFrames> result{};
        for (size_t index = 0; index < frameCount; ++index) {
            pixels[index] = std::make_unique<QByteArray>(std::move(readbackResults[index].data));
            auto* data = reinterpret_cast<uint8_t*>(pixels[index]->data());
            if (outputFormat == QRhiTexture::RGBA8) {
                const auto tick = Clock::now();
                rgbaToBgra(data, data, size_t(width) * height);
                inplaceConversionSeconds += elapsed(tick);
            }
            result[index] = SPRhiFrame{pixels[index].get(), data, size_t(pixels[index]->size())};
        }
        frames += frameCount;
        ownedFrames += frameCount;
        failed = false;
        // Publish only after readback, validation, and conversion succeeded.
        for (size_t index = 0; index < frameCount; ++index) {
            output[index] = result[index];
            pixels[index].release();
        }
    }
    const char* report() {
        require(thread == QThread::currentThreadId(), "RHI report must use creating thread");
        QJsonObject histogram;
        for (size_t index = 0; index < MaxBatchFrames; ++index)
            histogram.insert(QString::number(index + 1), qint64(batchHistogram[index]));
        QJsonObject report{
            {"graphics_api", QString::fromLatin1(api)}, {"qt_version", qVersion()},
            {"gpu_info", QJsonObject{{"renderer", QString::fromUtf8(rhi->driverInfo().deviceName)}, {"msaa_samples", 4}}},
            {"gpu_texture_cache_budget_bytes", qint64(budget)}, {"gpu_texture_cache_peak_bytes", qint64(texturePeak)},
            {"gpu_texture_cache_bytes", qint64(textureBytes)}, {"gpu_texture_cache_measured", false},
            {"texture_cache_accounting", "logical RGBA bytes; excludes driver allocations"},
            {"gpu_upload_seconds", uploadSeconds}, {"gpu_upload_bytes", qint64(uploadedBytes)},
            {"native_prepare_seconds", prepareSeconds}, {"native_begin_frame_seconds", beginFrameSeconds},
            {"gpu_submit_seconds", submitSeconds},
            {"synchronous_readback_seconds", readbackSeconds}, {"memory_copy_seconds", copySeconds},
            {"memory_copy_bytes", qint64(copiedFrames * uint64_t(width) * height * 4)},
            {"inplace_format_conversion_seconds", inplaceConversionSeconds},
            {"inplace_format_conversion_bytes", outputFormat == QRhiTexture::RGBA8
                ? qint64(ownedFrames * uint64_t(width) * height * 4) : qint64(0)},
            {"readback_seconds", readbackSeconds + copySeconds + inplaceConversionSeconds}, {"gpu_timestamp_enabled", timestamps},
            {"gpu_timestamp_samples", qint64(gpuSamples)}, {"gpu_execution_seconds", gpuSamples ? QJsonValue(gpuSeconds) : QJsonValue(QJsonValue::Null)},
            {"gpu_submitted_frame_count", qint64(frames)}, {"gpu_submission_count", qint64(submissions)},
            {"gpu_batch_size_histogram", histogram}, {"gpu_batch_peak_size", qint64(batchPeak)},
            {"readback_mode", batchPeak > 1 ? "rhi-batch-sync" : "rhi-sync"},
            {"owned_readback_frame_count", qint64(ownedFrames)}, {"copied_readback_frame_count", qint64(copiedFrames)},
            {"readback_format", outputFormat == QRhiTexture::BGRA8 ? "BGRA8" : "RGBA8"},
            {"readback_copy_path", ownedFrames && copiedFrames ? "mixed-owned-and-copy"
                : ownedFrames ? (outputFormat == QRhiTexture::BGRA8 ? "bgra-owned-buffer" : "rgba-inplace-sse2-swizzle")
                : copiedFrames ? (outputFormat == QRhiTexture::BGRA8 ? "bgra-memcpy" : "rgba-sse2-swizzle") : "not-submitted"},
            // Per-submit CPU staging estimate. Retained caller/writer frames
            // are accounted for separately by the export queue.
            {"readback_buffer_peak_bytes", qint64(cpuReadbackPeak)},
            {"readback_output_peak_bytes", qint64(outputPeak)},
            {"readback_staging_peak_bytes", qint64(stagingPeak)},
            {"readback_buffer_accounting", "per-submit CPU output estimate; excludes retained caller frames and Qt staging"},
            {"readback_staging_accounting", "logical Qt GPU-to-CPU staging estimate; excludes allocator and driver overhead"},
            {"framebuffer_estimated_bytes", qint64(width) * height * 20}
        };
        json = QJsonDocument(report).toJson(QJsonDocument::Compact);
        return json.constData();
    }
    ~Renderer() {
        // QRhi must outlive every resource, and the Vulkan instance must outlive QRhi.
        if (rhi) rhi->finish();
        textures.clear(); vertices.reset(); pipeline.reset(); sampler.reset();
        target.reset(); pass.reset(); msaa.reset(); resolve.reset(); rhi.reset();
    }
};
Renderer& owner(void* pointer) { require(pointer, "Null RHI handle"); return *static_cast<Renderer*>(pointer); }
template<class Operation> int guarded(Operation operation) {
    try { operation(); lastError.clear(); return 0; }
    catch (const std::exception& error) { lastError = error.what(); return 1; }
    catch (...) { lastError = "Unexpected native RHI failure"; return 1; }
}
}

uint32_t sprhi_abi_version() { return 3; }
void* sprhi_create(int32_t width, int32_t height, uint64_t budget, const char* api) {
    Renderer* result = nullptr;
    guarded([&] { require(api, "Null API name"); result = new Renderer(width, height, budget, api); });
    return result;
}
int sprhi_upload(void* p, uint64_t id, int32_t w, int32_t h, int32_t stride, const uint8_t* pixels) {
    return guarded([&] { owner(p).upload(id, w, h, stride, pixels); });
}
int sprhi_remove(void* p, uint64_t id) { return guarded([&] { owner(p).remove(id); }); }
int sprhi_submit(void* p, const SPRhiQuad* quads, size_t count, uint8_t* pixels, size_t capacity) {
    return guarded([&] { owner(p).submit(quads, count, pixels, capacity); });
}
int sprhi_submit_owned(void* p, const SPRhiQuad* quads, size_t count, SPRhiFrame* frame) {
    if (frame) *frame = {};
    return guarded([&] { owner(p).submitOwned(quads, count, frame); });
}
int sprhi_submit_batch_owned(void* p, const SPRhiBatchItem* items, size_t count, SPRhiFrame* frames) {
    if (frames && count <= MaxBatchFrames)
        std::fill_n(frames, count, SPRhiFrame{});
    return guarded([&] { owner(p).submitBatchOwned(items, count, frames); });
}
void sprhi_release_frame(void* pointer) { delete static_cast<QByteArray*>(pointer); }
const char* sprhi_report(void* p) {
    const char* result = nullptr;
    guarded([&] { result = owner(p).report(); });
    return result;
}
const char* sprhi_last_error(void*) { return lastError.constData(); }
int sprhi_close(void* p) {
    return guarded([&] { if (p) { require(owner(p).thread == QThread::currentThreadId(), "Close RHI on creating thread"); delete static_cast<Renderer*>(p); } });
}
