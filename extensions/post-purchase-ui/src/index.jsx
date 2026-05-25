/**
 * PostLift AI — Post-Purchase Upsell Extension
 *
 * 注文完了ページに表示されるワンクリックアップセル UI。
 * 1. shouldRender()  : オファーが存在するか確認（なければ非表示）
 * 2. render()        : オファー UI を表示、承諾/拒否を記録
 */
import {
  extend,
  render,
  BlockStack,
  Button,
  CalloutBanner,
  Heading,
  Image,
  Layout,
  TextContainer,
  Text,
  TextBlock,
  Separator,
  Money,
  useExtensionInput,
} from "@shopify/post-purchase-ui-extensions-react";

const APP_URL = "https://your-app.replit.app"; // 本番時は APP_URL 環境変数に合わせて変更

/**
 * shouldRender フック：オファーが存在する場合のみ UI を表示する
 */
extend("Checkout::PostPurchase::ShouldRender", async ({ inputData, storage }) => {
  const { initialPurchase, shop } = inputData;
  const orderId = initialPurchase.referenceId;
  const shopDomain = shop.domain;

  try {
    const resp = await fetch(
      `${APP_URL}/offers/current?order_id=${orderId}&shop_domain=${shopDomain}`
    );
    if (!resp.ok) return { render: false };

    const offer = await resp.json();
    await storage.update(offer); // offer データを render() に引き渡す
    return { render: true };
  } catch {
    return { render: false };
  }
});

/**
 * render フック：アップセル UI を描画する
 */
render("Checkout::PostPurchase::Render", () => <App />);

function App() {
  const { storage, inputData, applyChangeSet, done } = useExtensionInput();
  const offer = storage.initialData;
  const { initialPurchase, shop } = inputData;

  if (!offer) {
    done();
    return null;
  }

  const handleAccept = async () => {
    // Shopify Checkout にアップセル商品を追加
    await applyChangeSet({
      changes: [
        {
          type: "add_variant",
          variantId: offer.product_id,
          quantity: 1,
          discount: { value: 0, valueType: "percentage", title: "PostLift Upsell" },
        },
      ],
    });

    // バックエンドに承諾を記録
    await fetch(`${APP_URL}/webhooks/upsell/respond`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ offer_id: offer.offer_id, accepted: true }),
    });

    done();
  };

  const handleDecline = async () => {
    // バックエンドに拒否を記録
    await fetch(`${APP_URL}/webhooks/upsell/respond`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ offer_id: offer.offer_id, accepted: false }),
    });

    done();
  };

  return (
    <BlockStack spacing="loose">
      <CalloutBanner title="🎁 特別オファー — ワンクリックで追加購入">
        <Text>このご注文に限り、下記の商品を今すぐ追加できます。</Text>
      </CalloutBanner>

      <Layout
        media={[
          { viewportSize: "small", sizes: [1, 0], maxInlineSize: 0.9 },
          { viewportSize: "medium", sizes: [532, 0], maxInlineSize: 420 },
          { viewportSize: "large", sizes: [560, 340] },
        ]}
      >
        <BlockStack spacing="loose">
          <Heading>{offer.title}</Heading>
          <TextContainer>
            <TextBlock size="medium">
              <Money amount={String(offer.price)} currency="JPY" />
            </TextBlock>
          </TextContainer>

          <Separator />

          <BlockStack spacing="tight">
            <Button kind="primary" onPress={handleAccept}>
              ✅ ワンクリックで追加購入
            </Button>
            <Button kind="secondary" onPress={handleDecline}>
              今回はスキップ
            </Button>
          </BlockStack>
        </BlockStack>
      </Layout>
    </BlockStack>
  );
}
