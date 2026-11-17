const std = @import("std");
// No-op build: artifact is prebuilt by `sa build-lib` from pure SLA source.
// This build.zig only satisfies the installer's text-source-project gate.
pub fn build(b: *std.Build) void {
    _ = b.standardOptimizeOption(.{});
}
