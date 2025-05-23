// Initialize Stripe payment flow when the page loads
document.addEventListener('DOMContentLoaded', function () {
    // Get references to elements
    const planIdInput = document.getElementById('plan-id');
    const orderAmountInput = document.getElementById('plan-price');
    const paymentElementContainer = document.getElementById('payment-element-container');
    const paymentMessage = document.getElementById('payment-message');
    const submitButton = document.getElementById('submit-button');
    const buttonText = document.getElementById('button-text');
    const spinner = document.getElementById('spinner');
  
    // Only initialize if we're on the payment page
    if (!planIdInput || !paymentElementContainer) return;
  
    // Disable the submit button initially until Stripe elements are ready
    if (submitButton) {
      submitButton.disabled = true;
    }
  
    // Get data from the page
    const planId = planIdInput.value;
    const orderAmount = orderAmountInput.value;
    const stripePublishableKey = document.getElementById('stripe-publishable-key').value;
    const csrfToken = document.getElementById('csrf-token').value;
  
    // Initialize Stripe with publishable key and beta flag
    const stripe = Stripe(stripePublishableKey, {
      apiVersion: '2025-01-27.acacia; custom_checkout_beta=v1;',
    });
  
    console.log('Stripe initialized with version:', Stripe.version);
  
    let elements;
    let clientSecret;
    let customerId;
    let subscriptionId;
    let paymentId;
  
    // Fetch the checkout session from the server
    async function initialize() {
      try {
        // Create checkout session on the server
        const response = await fetch('/subscription/create-payment-intent', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken,
          },
          body: JSON.stringify({
            orderAmount: orderAmount,
            product_id: planId,
          })
        });
  
        const data = await response.json();
  
        if (response.ok) {
          if (data.redirect_url) {
            window.location.href = data.redirect_url;
          } else {
            // Store the client secret from the response
            clientSecret = data.clientSecret;
            customerId = data.customer_id;
            subscriptionId = data.subscription_id;
            paymentId = data.payment_id;
  
            // Log the client secret for debugging (redact in production)
            // console.log('Client secret received:', clientSecret);
  
            // Create the elements instance using the client secret
            const loader = 'auto';
            elements = stripe.elements({clientSecret, loader});
  
            // Create the Payment Element and mount it
            const paymentElement = elements.create('payment');
            paymentElement.mount('#payment-element-container');
            // Create and mount the linkAuthentication Element to enable autofilling customer payment details
            const linkAuthenticationElement = elements.create("linkAuthentication");
            linkAuthenticationElement.mount("#link-authentication-element");
  
            // Show the payment form
            paymentElementContainer.style.display = 'block';
  
            // Enable the submit button
            submitButton.disabled = false;
  
            const form = document.getElementById('payment-form');
            let submitted = false;
            form.addEventListener('submit', async (e) => {
              e.preventDefault();
  
              // Disable double submission of the form
              if (submitted) {
                return;
              }
              submitted = true;
              form.querySelector('button').disabled = true;
  
              // const nameInput = document.querySelector('#name');
  
              // Confirm the payment given the clientSecret
              // from the payment intent that was just created on
              // the server.
              const {error: stripeError, paymentIntent} = await stripe.confirmPayment({
                elements,
                redirect: 'if_required',
                // confirmParams: {
                //   return_url: `${window.location.origin}/subscription/payment-complete`,
                // }
              });
  
              if (stripeError) {
                addMessage(stripeError.message);
              } else if (paymentIntent && paymentIntent.status === 'succeeded') {
                await handleSuccessfulPayment(paymentIntent);
              }
            });
          }
        } else {
          // Show error message
          throw new Error(data.error || 'Failed to create checkout session');
        }
      } catch (error) {
        showError(error.message);
      }
    }
  
    // Function to handle successful payments
    async function handleSuccessfulPayment(paymentIntent) {
      console.log('Payment intent:', JSON.stringify(paymentIntent));
      try {
        // Notify the server of successful payment via POST
        const response = await fetch('/subscription/payment-complete', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
          },
          body: JSON.stringify({
            payment_intent_id: paymentIntent.id,
            plan_id: planId,
            customer_id: customerId,
            subscription_id: subscriptionId,
            payment_id: paymentId
          })
        });
  
        const data = await response.json();
  
        if (response.ok && data.success) {
          // Redirect to success page
          window.location.href = '/subscription/subscription-success';
        } else {
          throw new Error(data.error || 'Failed to record payment');
        }
      } catch (error) {
        showError(error.message || 'Payment successful, but failed to update subscription status');
      }
    }
  
    // Helper function to display error messages
    function showError(message) {
      paymentMessage.textContent = message || 'An unknown error occurred';
      paymentMessage.style.display = 'block';
  
      // Reset button visual state (spinner/text) if an error occurs.
      // The button itself remains disabled if Stripe setup hasn't completed.
      if (buttonText) {
        buttonText.style.display = 'inline-block';
      }
      if (spinner) {
        spinner.style.display = 'none';
      }
    }
  
    // Start the payment flow
    initialize();
  });
  