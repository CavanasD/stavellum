#version 440
layout(binding = 0) uniform sampler2D image;
layout(location = 0) in vec2 v_uv;
layout(location = 1) in vec4 v_color;
layout(location = 0) out vec4 fragColor;
void main() {
    fragColor = texture(image, v_uv) * v_color;
}
