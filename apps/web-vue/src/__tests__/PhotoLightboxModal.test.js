import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import PhotoLightboxModal from '../components/PhotoLightboxModal.vue'

describe('PhotoLightboxModal.vue - Evidence Photo Viewer & Zoom Controls', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  const mockPhotos = [
    {
      id: 'p1',
      filename: 'crushed_box.jpg',
      description: 'Pallet 3 carton crushed',
      url: 'https://example.com/crushed.jpg',
    },
    {
      id: 'p2',
      filename: 'expired_lot.jpg',
      description: 'Expired lot label',
      data_base64: 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==',
      content_type: 'image/jpeg',
    },
  ]

  it('renders when show is true with photo metadata and image', () => {
    const wrapper = mount(PhotoLightboxModal, {
      props: {
        show: true,
        photos: mockPhotos,
        initialIndex: 0,
      },
    })

    expect(wrapper.find('.lightbox-overlay').exists()).toBe(true)
    expect(wrapper.text()).toContain('crushed_box.jpg')
    expect(wrapper.text()).toContain('1 / 2')
    expect(wrapper.find('.lightbox-image').attributes('src')).toBe('https://example.com/crushed.jpg')
    expect(wrapper.text()).toContain('Pallet 3 carton crushed')
  })

  it('navigates to next and previous photos', async () => {
    const wrapper = mount(PhotoLightboxModal, {
      props: {
        show: true,
        photos: mockPhotos,
        initialIndex: 0,
      },
    })

    const nextBtn = wrapper.find('.nav-next')
    await nextBtn.trigger('click')

    expect(wrapper.text()).toContain('expired_lot.jpg')
    expect(wrapper.text()).toContain('2 / 2')
    expect(wrapper.find('.lightbox-image').attributes('src')).toContain('data:image/jpeg;base64,')

    const prevBtn = wrapper.find('.nav-prev')
    await prevBtn.trigger('click')

    expect(wrapper.text()).toContain('crushed_box.jpg')
    expect(wrapper.text()).toContain('1 / 2')
  })

  it('supports zoom in, zoom out, and reset zoom', async () => {
    const wrapper = mount(PhotoLightboxModal, {
      props: {
        show: true,
        photos: mockPhotos,
        initialIndex: 0,
      },
    })

    expect(wrapper.text()).toContain('100%')

    const zoomInBtn = wrapper.find('button[title="Zoom In"]')
    await zoomInBtn.trigger('click')
    expect(wrapper.text()).toContain('125%')

    const zoomOutBtn = wrapper.find('button[title="Zoom Out"]')
    await zoomOutBtn.trigger('click')
    expect(wrapper.text()).toContain('100%')
  })

  it('emits close event when clicking close button or backdrop', async () => {
    const wrapper = mount(PhotoLightboxModal, {
      props: {
        show: true,
        photos: mockPhotos,
        initialIndex: 0,
      },
    })

    const closeBtn = wrapper.find('.btn-close')
    await closeBtn.trigger('click')

    expect(wrapper.emitted('close')).toBeTruthy()
  })
})
