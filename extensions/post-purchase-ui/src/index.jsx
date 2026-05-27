import {
  extend,
  render,
  BlockStack,
  Button,
  CalloutBanner,
  Heading,
  Layout,
  Text,
  TextBlock,
  TextContainer,
  Separator,
  Money,
  useExtensionInput,
} from "@shopify/post-purchase-ui-extensions-react";

const APP_URL = "https://your-app.example.com";

extend("Checkout::PostPurchase::ShouldRender", async ({ inputData, storage }) => {
  const { initialPurchase, shop } = inputData;
  const orderId = initialPurchase.referenceId;
  const shopDomain = shop.domain;

  try {
    const resp = await fetch(
      `${APP_URL}/offers/current?order_id=${encodeURIComponent(orderId)}&shop_domain=${encodeURIComponent(shopDomain)}`
    );
    if (!resp.ok) return { render: false };

    const offer = await resp.json();
    if (!offer?.offer_id) return { render: false };

    await storage.update(offer);
    return { render: true };
  } catch {
    return { render: false };
  }
});

render("Checkout::PostPurchase::Render", () => <App />);

function App() {
  const { storage, applyChangeSet, done } = useExtensionInput();
  const offer = storage.initialData;

  if (!offer) {
    done();
    return null;
  }

  const recordResponse = async (accepted) => {
    await fetch(`${APP_URL}/webhooks/upsell/respond`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ offer_id: offer.offer_id, accepted }),
    });
  };

  const handleAccept = async () => {
    await applyChangeSet({
      changes: [
        {
          type: "add_variant",
          variantId: offer.variant_id || offer.product_id,
          quantity: 1,
          discount: { value: 0, valueType: "percentage", title: "PostLift Upsell" },
        },
      ],
    });

    await recordResponse(true);
    done();
  };

  const handleDecline = async () => {
    await recordResponse(false);
    done();
  };

  return (
    <BlockStack spacing="loose">
      <CalloutBanner title="Special offer for your order">
        <Text>{offer.copy_text || "Add this recommended item to your order with one click."}</Text>
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
              Add to my order
            </Button>
            <Button kind="secondary" onPress={handleDecline}>
              No thanks
            </Button>
          </BlockStack>
        </BlockStack>
      </Layout>
    </BlockStack>
  );
}
