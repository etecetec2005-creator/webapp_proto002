import streamlit as st
import google.generativeai as genai
from PIL import Image
import io
import os
import base64

# --- セキュリティ設定 ---
api_key = st.secrets.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
if not api_key:
    st.error("APIキーが設定されていません。StreamlitのSecretsに登録してください。")
    st.stop()

genai.configure(api_key=api_key)

# --- 基本設定 ---
st.set_page_config(page_title="Railway Electric Facility Checker", layout="centered")
st.title("🚉 設備の状態は？")

# カテゴリ選択
category = st.selectbox(
    "判定カテゴリを選択してください",
    [
        "すべて",
        "破損はあるか（損傷、き裂、折損、切れ など）",
        "変質はあるか（腐食、劣化、さび、電色、変色、黒色化、地金露出 など）",
        "変形はあるか（変形、わん曲、ねじれ、傾斜、膨らみ、痩せ など）",
        "欠落はあるか（脱落、ゆるみ、欠品 など）",
        "付着はあるか（汚損、漏油、漏水、ツララ など）",
        "不要な介在物はあるか（ナット等金属、虫・小動物、排泄物 など）",
        "その他"
    ]
)

# 入力ソースの選択（カメラまたはアップロード）
input_method = st.radio("入力方法を選択してください", ["カメラで撮影", "画像をアップロード"])

img_file = None
if input_method == "カメラで撮影":
    img_file = st.camera_input("設備を撮影", key="railway_camera_v1")
else:
    img_file = st.file_uploader("画像を選択してください", type=["jpg", "jpeg", "png"], key="railway_upload_v1")

if img_file:
    # 1. 画像の読み込み
    img = Image.open(img_file)
    width, height = img.size 
    st.image(img, caption="解析・保存プロセスを実行中...")

    # 2. AI解析（判定とタイトル付与）
    ai_analysis = ""
    ai_title = "設備判定"
    
    with st.spinner("AIが詳細に解析中..."):
        try:
            model = genai.GenerativeModel('gemini-2.5-flash-lite')
            
            # 専門的な判定用プロンプト（精緻な観察指示を追加）
            prompt = f"""
あなたは保守点検の専門家です。
提出された写真（道具、設備等）を、肉眼では見落としがちな細部まで**「精緻に観察」**し、プロの視点で分析して結果を報告してください。

【確認カテゴリ】: {category}

【指示】
1. 画像全体を隅々まで走査し、微細な表面の状態変化（小さなクラック、わずかな変色、ミリ単位の歪み等）を逃さず特定してください。
2. 異常の有無を専門用語（{category}に関連する用語）を用いて具体的に判定してください。
3. 異常がある場合は、その「正確な箇所」「推定される原因」「進行度（程度）」を詳しく推測してください。
4. 最後に、この写真にふさわしい「20文字以内のタイトル」を1行だけで出力してください。

【タイトル付与の留意事項】
- 写真に設備等が写っている場合、写実的で具体的なタイトルにすること。
- 文字や数字が写っている場合はタイトルに含めること（ただし、文字・数字のみは不可）。
- タイトルは出力の最後の一行に「タイトル：〇〇」の形式で記述してください。
"""
            response = model.generate_content([prompt, img])
            
            if response and response.text:
                full_text = response.text
                # タイトル部分の抽出を試みる
                if "タイトル：" in full_text:
                    parts = full_text.split("タイトル：")
                    ai_analysis = parts[0].strip()
                    ai_title = parts[1].strip().replace("\n", "").replace("/", "-").replace(" ", "")
                else:
                    ai_analysis = full_text
                    ai_title = "設備判定結果"
                
                # 表示用にタイトルを20文字でカット
                ai_title = ai_title[:20]

            st.subheader("📋 判定結果")
            st.write(ai_analysis)

        except Exception as e:
            st.error(f"⚠️ AI解析エラー: {e}")

    # 3. 画像のBase64変換
    buffered = io.BytesIO()
    img.save(buffered, format="JPEG", quality=100, subsampling=0)
    img_str = base64.b64encode(buffered.getvalue()).decode()

    # 4. 全自動JavaScript（住所・駅取得 ＋ 文字埋め込み ＋ JPG保存）
    st.success(f"保存用タイトル: {ai_title}")
    
    auto_save_script = f"""
    <div id="status" style="font-size:12px; color:gray; padding:10px; background:#f9f9f9; border-radius:5px;">
        📍 位置情報と駅名を特定して、画像を保存します...
    </div>
    <script>
    (async function() {{
        const status = document.getElementById('status');
        const aiTitle = "{ai_title}";
        const imgBase64 = "data:image/jpeg;base64,{img_str}";
        const oW = {width};
        const oH = {height};

        const now = new Date();
        const dateStr = now.getFullYear().toString().slice(-2) + 
                        ('0' + (now.getMonth() + 1)).slice(-2) + 
                        ('0' + now.getDate()).slice(-2) + 
                        ('0' + now.getHours()).slice(-2) + 
                        ('0' + now.getMinutes()).slice(-2);

        navigator.geolocation.getCurrentPosition(
            async (pos) => {{
                const lat = pos.coords.latitude;
                const lon = pos.coords.longitude;
                let finalAddr = "住所不明";
                let stationName = "駅名不明";

                try {{
                    const addrRes = await fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${{lat}}&lon=${{lon}}&zoom=18&addressdetails=1&accept-language=ja`);
                    const addrData = await addrRes.json();
                    
                    if (addrData && addrData.address) {{
                        const a = addrData.address;
                        const parts = [
                            a.city || a.town || a.village || "",
                            a.city_district || "",
                            a.suburb || "",
                            a.neighbourhood || "",
                            a.road || ""
                        ];
                        finalAddr = [...new Set(parts.filter(p => p !== ""))].join("");
                        finalAddr = finalAddr.replace(/日本|〒[0-9-]+/g, "").trim();
                    }}

                    const stRes = await fetch(`https://express.heartrails.com/api/json?method=getStations&x=${{lon}}&y=${{lat}}`);
                    const stData = await stRes.json();
                    if (stData.response && stData.response.station && stData.response.station.length > 0) {{
                        stationName = stData.response.station[0].name + "駅";
                    }}
                }} catch (e) {{
                    console.error(e);
                }}
                processAndSave(finalAddr, stationName);
            }},
            (err) => {{ processAndSave("位置情報なし", "駅名なし"); }},
            {{ enableHighAccuracy: true, timeout: 7000 }}
        );

        function processAndSave(addr, stn) {{
            const displayText = aiTitle + " _ " + addr + " _ " + stn;
            const safeAddr = addr.replace(/[/\\\\?%*:|"<>]/g, '-');
            const fileName = dateStr + "_" + aiTitle + "_" + safeAddr + "_" + stn + ".jpg";

            const canvas = document.createElement('canvas');
            const ctx = canvas.getContext('2d');
            const img = new Image();
            
            img.onload = function() {{
                canvas.width = oW;
                canvas.height = oH;
                ctx.drawImage(img, 0, 0, oW, oH);
                
                const fontSize = Math.floor(oH / 35); 
                ctx.font = "bold " + fontSize + "px sans-serif";
                ctx.textBaseline = "top";
                const padding = fontSize / 2;
                const textWidth = ctx.measureText(displayText).width;
                
                ctx.fillStyle = "rgba(0, 0, 0, 0.6)";
                ctx.fillRect(20, 20, textWidth + (padding * 2), fontSize + (padding * 2));
                
                ctx.fillStyle = "white";
                ctx.fillText(displayText, 20 + padding, 20 + padding);
                
                const link = document.createElement('a');
                link.download = fileName;
                link.href = canvas.toDataURL('image/jpeg', 1.0);
                link.click();
                
                status.style.color = "green";
                status.innerText = "✅ 保存完了: " + fileName;
            }};
            img.src = imgBase64;
        }}
    }})();
    </script>
    """
    st.components.v1.html(auto_save_script, height=120)
