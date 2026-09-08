import com.boohee.ai.*;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.*;
import java.nio.file.*;
import java.util.*;

/**
 * 流式图片识别示例
 *
 * 用法:
 *   java FoodImageRecognizeStream                              # 默认图片
 *   java FoodImageRecognizeStream --url https://xxx.jpg        # 按URL识别
 *   java FoodImageRecognizeStream --base64 /path/to/image.jpg  # 按base64识别
 *   java FoodImageRecognizeStream --url https://xxx.jpg --ingredients sugar,purine --with-nrv
 */
public class FoodImageRecognizeStream {

    static class FoodImageRecognizeStreamReq implements BaseReq {
        private final Map<String, Object> body = new HashMap<>();

        FoodImageRecognizeStreamReq(String imageUrl, String imageData,
                                    String ingredients, boolean withNrv) {
            if (imageUrl != null) body.put("image_url", imageUrl);
            if (imageData != null) body.put("image_data", imageData);
            if (ingredients != null) body.put("ingredients", ingredients);
            if (withNrv) body.put("with_nrv", true);
        }

        @Override public HttpMethod getMethod() { return HttpMethod.POST; }
        @Override public String getUrl() { return "/open-apis/v1/food/image_recongize_stream"; }
        @Override public Map<String, Object> getBody() { return body; }
    }

    static void loadEnv() throws IOException {
        Path envPath = Paths.get(".env");
        if (!Files.exists(envPath)) {
            System.out.println("请先复制 .env.example 为 .env 并填入真实凭证");
            System.exit(1);
        }
        for (String line : Files.readAllLines(envPath)) {
            line = line.trim();
            if (line.isEmpty() || line.startsWith("#")) continue;
            int idx = line.indexOf('=');
            if (idx > 0) {
                String key = line.substring(0, idx).trim();
                String value = line.substring(idx + 1).trim();
                if (System.getenv(key) == null) {
                    System.setProperty(key, value);
                }
            }
        }
    }

    @SuppressWarnings("unchecked")
    public static void main(String[] args) throws Exception {
        loadEnv();

        String apiKey = System.getProperty("BOOHEE_API_KEY", System.getenv("BOOHEE_API_KEY"));
        if (apiKey == null || apiKey.isEmpty()) {
            System.out.println("BOOHEE_API_KEY 未配置");
            System.exit(1);
        }

        String baseURL = System.getProperty("BOOHEE_BASE_URL",
                System.getenv().getOrDefault("BOOHEE_BASE_URL", "https://api.boohee.com"));

        BooheeClient client = BooheeClient.builder()
                .authMode(AuthMode.API_KEY)
                .apiKey(apiKey)
                .baseURL(baseURL)
                .build();

        // 解析参数
        String imageUrl = null, imageData = null, ingredients = null;
        boolean withNrv = false;
        for (int i = 0; i < args.length; i++) {
            switch (args[i]) {
                case "--url": imageUrl = args[++i]; break;
                case "--base64":
                    byte[] fileBytes = Files.readAllBytes(Paths.get(args[++i]));
                    imageData = Base64.getEncoder().encodeToString(fileBytes);
                    break;
                case "--ingredients": ingredients = args[++i]; break;
                case "--with-nrv": withNrv = true; break;
            }
        }
        if (imageUrl == null && imageData == null) {
            imageUrl = "https://img.boohee.cn/ghp/foods/000/000/001/140_1.jpg";
        }

        String label = imageUrl != null ? imageUrl : "base64数据";
        System.out.println("识别图片: " + label + "\n");
        System.out.println("流式输出:");

        ObjectMapper mapper = new ObjectMapper();
        StringBuilder fullContent = new StringBuilder();
        List<Map<String, Object>> foodInfo = new ArrayList<>();

        client.executeStream(new FoodImageRecognizeStreamReq(imageUrl, imageData, ingredients, withNrv), chunk -> {
            try {
                Map<String, Object> event = mapper.readValue(chunk, Map.class);
                int resultCode = event.get("result_code") instanceof Number
                        ? ((Number) event.get("result_code")).intValue() : -1;
                if (resultCode != 0) {
                    System.out.println("\n错误: " + event.get("message"));
                    System.exit(1);
                }
                Map<String, Object> data = (Map<String, Object>) event.get("data");
                if (data == null) return;

                String content = (String) data.get("content");
                if (content != null && !content.isEmpty()) {
                    System.out.print(content);
                    fullContent.append(content);
                }
                if (Boolean.TRUE.equals(data.get("end"))) {
                    List<Map<String, Object>> fi = (List<Map<String, Object>>) data.get("food_info");
                    if (fi != null) foodInfo.addAll(fi);
                }
            } catch (Exception e) {
                // 忽略解析错误
            }
        });

        System.out.println();

        if (!foodInfo.isEmpty()) {
            System.out.printf("%n--- 识别到 %d 个食物 ---%n%n", foodInfo.size());
            for (Map<String, Object> food : foodInfo) {
                System.out.printf("  %s  估重: %sg  热量: %skcal/100g  蛋白质: %sg  脂肪: %sg  碳水: %sg%n",
                        food.getOrDefault("name", "?"),
                        food.getOrDefault("amount", "?"),
                        food.getOrDefault("calories", "?"),
                        food.getOrDefault("protein", "?"),
                        food.getOrDefault("fat", "?"),
                        food.getOrDefault("carbohydrate", "?"));
                List<Map<String, Object>> ings = (List<Map<String, Object>>) food.get("ingredients");
                if (ings != null && !ings.isEmpty()) {
                    List<String> ingStrs = new ArrayList<>();
                    for (Map<String, Object> ing : ings) {
                        ingStrs.add(ing.get("name") + ": " + ing.get("value") + ing.get("unit"));
                    }
                    System.out.printf("    营养素: %s%n", String.join(", ", ingStrs));
                }
                List<Map<String, Object>> nrvs = (List<Map<String, Object>>) food.get("nrv");
                if (nrvs != null && !nrvs.isEmpty()) {
                    List<String> nrvStrs = new ArrayList<>();
                    for (Map<String, Object> nrv : nrvs) {
                        nrvStrs.add(nrv.get("name") + ": " + nrv.get("value"));
                    }
                    System.out.printf("    NRV: %s%n", String.join(", ", nrvStrs));
                }
                System.out.println();
            }
        }
    }
}
