import { BASE_URL } from "./config";

/**
 * 通用文件上传（图片 + 视频）。
 * @param {string} tempFilePath - 本地临时文件路径
 * @param {string} [fileType] - 文件类别提示 'image' | 'video'
 * @returns {Promise<{url: string, type: string}>}
 */
export function uploadFile(tempFilePath, fileType) {
  return new Promise((resolve, reject) => {
    const token = uni.getStorageSync("access_token");

    // 根据文件路径后缀推断 MIME
    let mimeType = "image/jpeg";
    const lower = tempFilePath.toLowerCase();
    if (lower.endsWith(".mp4")) mimeType = "video/mp4";
    else if (lower.endsWith(".webm")) mimeType = "video/webm";
    else if (lower.endsWith(".png")) mimeType = "image/png";
    else if (lower.endsWith(".gif")) mimeType = "image/gif";
    else if (lower.endsWith(".webp")) mimeType = "image/webp";

    uni.uploadFile({
      url: `${BASE_URL}/upload`,
      filePath: tempFilePath,
      name: "file",
      fileType: fileType || (mimeType.startsWith("video") ? "video" : "image"),
      header: token ? { Authorization: `Bearer ${token}` } : {},
      success: (res) => {
        if (res.statusCode === 200) {
          const data = JSON.parse(res.data);
          resolve(data);
        } else {
          reject(new Error("上传失败"));
        }
      },
      fail: (err) => {
        reject(new Error(err?.errMsg || "上传失败"));
      },
    });
  });
}

/**
 * 兼容旧接口：上传图片，返回 URL 字符串。
 */
export function uploadImage(tempFilePath) {
  return uploadFile(tempFilePath, "image").then((r) => r.url);
}
